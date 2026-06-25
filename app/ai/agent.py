"""LangChain-powered conversational agent for museum ticket booking."""

import uuid
import json
from datetime import datetime
from typing import Optional
from app.ai.prompts import (
    MUSEUM_SYSTEM_PROMPT,
    BOOKING_CONFIRMATION_TEMPLATE,
    PAYMENT_PROMPT_TEMPLATE,
    TICKET_CONFIRMED_TEMPLATE,
)
from app.ai.nlp_processor import NLPProcessor
from app.services.ticket_service import TicketService
from app.services.payment_service import PaymentService
from app.database.connection import get_collection
from app.core.config import settings


class MuseumAgent:
    """Conversational AI agent for museum ticket booking."""

    def __init__(self):
        self.nlp = NLPProcessor()
        self.llm_available = False
        self._init_llm()

    def _init_llm(self):
        """Initialize the LLM (Google Gemini)."""
        try:
            if settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY != "demo_key_replace_with_real":
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.llm_available = True
                print("✅ Gemini LLM initialized successfully")
            else:
                print("⚠️ No valid API key - using rule-based responses")
        except Exception as e:
            print(f"⚠️ LLM init failed: {e} - using rule-based responses")

    async def _get_or_create_session(self, session_id: Optional[str] = None) -> dict:
        """Get or create a chat session."""
        chat_col = get_collection("chat_logs")

        if session_id:
            session = await chat_col.find_one({"session_id": session_id})
            if session:
                return session

        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        session = {
            "session_id": new_session_id,
            "messages": [],
            "language": "en",
            "started_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "booking_context": {
                "state": "greeting",
                "ticket_type": None,
                "visit_date": None,
                "num_tickets": None,
                "visitor_category": None,
                "visitor_name": None,
                "visitor_email": None,
                "visitor_phone": None,
                "exhibition_id": None,
                "show_time": None,
            },
        }
        await chat_col.insert_one(session)
        return session

    async def _update_session(self, session_id: str, updates: dict):
        """Update a chat session."""
        chat_col = get_collection("chat_logs")
        updates["last_activity"] = datetime.utcnow()
        await chat_col.update_one(
            {"session_id": session_id},
            {"$set": updates}
        )

    async def _add_message(self, session_id: str, role: str, content: str):
        """Add a message to the session history."""
        chat_col = get_collection("chat_logs")
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await chat_col.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message},
                "$set": {"last_activity": datetime.utcnow()},
            },
        )

    async def _generate_llm_response(self, messages: list, context: dict) -> str:
        """Generate a response using Google Gemini."""
        if not self.llm_available:
            return None

        try:
            # Build conversation history for context
            conversation = f"{MUSEUM_SYSTEM_PROMPT}\n\n"
            conversation += f"Current booking context: {json.dumps(context, default=str)}\n\n"

            for msg in messages[-10:]:  # Last 10 messages for context
                role = "User" if msg["role"] == "user" else "Assistant"
                conversation += f"{role}: {msg['content']}\n"

            response = self.model.generate_content(conversation)
            return response.text
        except Exception as e:
            print(f"LLM Error: {e}")
            return None

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Process a user message and return a response."""

        # Get or create session
        session = await self._get_or_create_session(session_id)
        session_id = session["session_id"]
        context = session.get("booking_context", {"state": "greeting"})

        # Extract entities from user message
        entities = self.nlp.extract_all_entities(message)

        # Detect language
        if entities.get("language") and entities["language"] != "en":
            await self._update_session(session_id, {"language": entities["language"]})

        # Add user message to history
        await self._add_message(session_id, "user", message)

        # Process based on current state
        response_data = await self._handle_state(
            message, entities, context, session, user_id
        )

        # Try LLM enhancement if available
        if self.llm_available and response_data.get("use_llm", False):
            llm_response = await self._generate_llm_response(
                session.get("messages", []) + [{"role": "user", "content": message}],
                context
            )
            if llm_response:
                response_data["reply"] = llm_response

        # Add assistant response to history
        await self._add_message(session_id, "assistant", response_data["reply"])

        return {
            "reply": response_data["reply"],
            "session_id": session_id,
            "action": response_data.get("action"),
            "data": response_data.get("data"),
        }

    async def _handle_state(
        self, message: str, entities: dict, context: dict, session: dict, user_id: str
    ) -> dict:
        """Handle the conversation based on current booking state."""
        state = context.get("state", "greeting")
        session_id = session["session_id"]
        msg_lower = message.lower().strip()

        # Check for cancel/restart commands
        if any(word in msg_lower for word in ['cancel', 'restart', 'start over', 'reset']):
            await self._update_session(session_id, {
                "booking_context": {"state": "greeting"}
            })
            return {
                "reply": "No problem! Let's start fresh. 🏛️\n\nWelcome to the National Heritage Museum! How can I help you today?\n\n1. 🎫 Book Tickets\n2. 📋 View Exhibitions\n3. ℹ️ Museum Information\n4. 📊 Check Availability\n5. 🔍 Look up a Booking",
                "action": "reset",
            }

        # Check for booking lookup
        if any(word in msg_lower for word in ['lookup', 'look up', 'check booking', 'find booking', 'booking status']):
            return await self._handle_booking_lookup(msg_lower, session_id)

        # Route to appropriate handler
        handlers = {
            "greeting": self._handle_greeting,
            "select_ticket_type": self._handle_ticket_type,
            "select_date": self._handle_date,
            "select_quantity": self._handle_quantity,
            "select_category": self._handle_category,
            "select_exhibition": self._handle_exhibition,
            "select_show_time": self._handle_show_time,
            "collect_name": self._handle_name,
            "collect_email": self._handle_email,
            "collect_phone": self._handle_phone,
            "confirm_booking": self._handle_confirmation,
            "payment": self._handle_payment,
        }

        handler = handlers.get(state, self._handle_greeting)
        return await handler(message, entities, context, session_id, user_id)

    async def _handle_greeting(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower()

        if any(word in msg_lower for word in ['book', 'ticket', 'buy', 'purchase', 'reserve']):
            context["state"] = "select_ticket_type"
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": "Great! Let's book your tickets! 🎫\n\nWhat type of ticket would you like?\n\n1. 🚶 **Gate Entry** - Basic museum admission\n2. 🎨 **Exhibition** - Entry + Special exhibition\n3. 🎭 **Show** - Entry + Planetarium/Theater show\n4. 🗣️ **Guided Tour** - Entry + Expert-guided tour\n5. 🎁 **Combo Package** - Entry + Exhibition + Tour *(15% OFF!)*\n\nJust type the number or the ticket type!",
                "action": "show_ticket_types",
            }

        if any(word in msg_lower for word in ['exhibition', 'exhibit', 'what\'s on', 'whats on', 'display']):
            exhibitions = await TicketService.get_exhibitions()
            if exhibitions:
                reply = "🎨 **Current Exhibitions:**\n\n"
                for i, ex in enumerate(exhibitions, 1):
                    reply += f"{i}. **{ex['name']}**\n"
                    reply += f"   📝 {ex['description']}\n"
                    reply += f"   📅 {ex['start_date']} to {ex['end_date']}\n"
                    reply += f"   💰 ₹{ex['ticket_price']} (plus gate entry)\n\n"
                reply += "\nWould you like to book tickets for any exhibition? 🎫"
            else:
                reply = "📋 No special exhibitions are currently running. But our permanent collections are always available!\n\nWould you like to book a gate entry ticket?"
            return {"reply": reply, "action": "show_exhibitions", "use_llm": True}

        if any(word in msg_lower for word in ['price', 'cost', 'fee', 'how much', 'pricing', 'rate']):
            return {
                "reply": "💰 **Museum Pricing:**\n\n**Gate Entry:**\n• Adult: ₹50\n• Child (under 12): ₹20\n• Student (with ID): ₹30\n• Senior (60+): ₹25\n• Foreign Tourist: ₹200\n\n**Add-ons:**\n• Guided Tour: +₹100\n• Exhibition: Varies by exhibition\n• Combo (Entry + Exhibition + Tour): **15% discount!**\n\nWould you like to book tickets? 🎫",
                "action": "show_pricing",
            }

        if any(word in msg_lower for word in ['help', 'what can you', 'options', 'menu']):
            return {
                "reply": "I can help you with:\n\n1. 🎫 **Book Tickets** - Gate entry, exhibitions, shows, tours\n2. 📋 **View Exhibitions** - See current exhibitions\n3. 💰 **Pricing** - Check ticket prices\n4. 📊 **Check Availability** - See if tickets are available\n5. 🔍 **Look up Booking** - Check an existing booking\n6. ℹ️ **Museum Info** - Timings, directions, etc.\n\nJust tell me what you need!",
            }

        if any(word in msg_lower for word in ['availability', 'available', 'check date']):
            context["state"] = "select_date"
            context["checking_availability"] = True
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": "📊 **Check Availability**\n\nWhich date would you like to check?\n\nYou can say:\n• A specific date (e.g., 2026-03-15)\n• 'Today' or 'Tomorrow'\n• 'This weekend'",
            }

        # Default greeting
        return {
            "reply": "🏛️ **Welcome to the National Heritage Museum!**\n\nI'm Heritage Guide, your AI assistant. I can help you with:\n\n1. 🎫 **Book Tickets** - Gate entry, exhibitions, shows & tours\n2. 📋 **View Exhibitions** - Current & upcoming exhibitions\n3. 💰 **Check Pricing** - Ticket prices & discounts\n4. 📊 **Check Availability** - Date-wise availability\n5. 🔍 **Look up Booking** - Check booking status\n\nHow can I help you today?",
            "use_llm": True,
        }

    async def _handle_ticket_type(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower().strip()

        ticket_type = entities.get("ticket_type")

        # Also check for number selection
        if not ticket_type:
            if '1' in msg_lower or 'gate' in msg_lower or 'basic' in msg_lower:
                ticket_type = "gate_entry"
            elif '2' in msg_lower or 'exhibition' in msg_lower:
                ticket_type = "exhibition"
            elif '3' in msg_lower or 'show' in msg_lower:
                ticket_type = "show"
            elif '4' in msg_lower or 'tour' in msg_lower or 'guide' in msg_lower:
                ticket_type = "guided_tour"
            elif '5' in msg_lower or 'combo' in msg_lower:
                ticket_type = "combo"

        if ticket_type:
            context["ticket_type"] = ticket_type
            context["state"] = "select_date"
            await self._update_session(session_id, {"booking_context": context})

            type_labels = {
                "gate_entry": "🚶 Gate Entry",
                "exhibition": "🎨 Exhibition",
                "show": "🎭 Show",
                "guided_tour": "🗣️ Guided Tour",
                "combo": "🎁 Combo Package (15% OFF!)",
            }

            return {
                "reply": f"Excellent choice! **{type_labels.get(ticket_type, ticket_type)}**\n\n📅 When would you like to visit?\n\nYou can say:\n• A specific date (e.g., 2026-03-15)\n• 'Today' or 'Tomorrow'\n• 'This weekend'\n• 'Next week'",
            }

        return {
            "reply": "I didn't quite catch that. Please select a ticket type:\n\n1. 🚶 Gate Entry\n2. 🎨 Exhibition\n3. 🎭 Show\n4. 🗣️ Guided Tour\n5. 🎁 Combo Package\n\nJust type the number or name!",
        }

    async def _handle_date(self, message, entities, context, session_id, user_id):
        visit_date = entities.get("date")

        if visit_date:
            # Check if just checking availability
            if context.get("checking_availability"):
                availability = await TicketService.check_availability(visit_date, context.get("ticket_type", "gate_entry"))
                context.pop("checking_availability", None)
                context["state"] = "greeting"
                await self._update_session(session_id, {"booking_context": context})

                status_emoji = "✅" if availability["is_available"] else "❌"
                return {
                    "reply": f"📊 **Availability for {visit_date}:**\n\n{status_emoji} **{availability['available']}** tickets available out of {availability['total_capacity']}\n🎫 Already booked: {availability['booked']}\n\nWould you like to book tickets for this date?",
                    "data": availability,
                }

            context["visit_date"] = visit_date
            context["state"] = "select_quantity"
            await self._update_session(session_id, {"booking_context": context})

            return {
                "reply": f"📅 Visit date set to **{visit_date}**\n\n🔢 How many tickets would you like? (1-20)",
            }

        return {
            "reply": "I couldn't understand the date. Please provide a valid date:\n\n• Format: YYYY-MM-DD (e.g., 2026-03-15)\n• Or say: 'today', 'tomorrow', 'this weekend'",
        }

    async def _handle_quantity(self, message, entities, context, session_id, user_id):
        num_tickets = entities.get("number")

        if not num_tickets:
            try:
                num_tickets = int(message.strip())
            except (ValueError, TypeError):
                pass

        if num_tickets and 1 <= num_tickets <= 20:
            context["num_tickets"] = num_tickets
            context["state"] = "select_category"
            await self._update_session(session_id, {"booking_context": context})

            return {
                "reply": f"🔢 **{num_tickets} ticket(s)** - Got it!\n\n👤 What category of visitor?\n\n1. 👨 **Adult** - ₹50\n2. 👶 **Child** (under 12) - ₹20\n3. 🎓 **Student** (with ID) - ₹30\n4. 👴 **Senior** (60+) - ₹25\n5. 🌍 **Foreign Tourist** - ₹200\n\nType the number or category name!",
            }

        return {
            "reply": "Please enter a valid number of tickets (1-20).\n\n🔢 How many tickets do you need?",
        }

    async def _handle_category(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower().strip()
        category = entities.get("visitor_category")

        if not category:
            if '1' in msg_lower:
                category = "adult"
            elif '2' in msg_lower:
                category = "child"
            elif '3' in msg_lower:
                category = "student"
            elif '4' in msg_lower:
                category = "senior"
            elif '5' in msg_lower:
                category = "foreign_tourist"

        if category:
            context["visitor_category"] = category

            # If exhibition or show or combo, ask for exhibition selection
            if context.get("ticket_type") in ["exhibition", "show", "combo"]:
                context["state"] = "select_exhibition"
                await self._update_session(session_id, {"booking_context": context})

                exhibitions = await TicketService.get_exhibitions()
                if exhibitions:
                    reply = "🎨 **Select an Exhibition:**\n\n"
                    for i, ex in enumerate(exhibitions, 1):
                        reply += f"{i}. **{ex['name']}** - ₹{ex['ticket_price']}\n"
                        reply += f"   {ex['description'][:80]}...\n\n"
                    reply += "Type the number of your choice!"
                    return {"reply": reply}
                else:
                    # No exhibitions - skip to name
                    context["state"] = "collect_name"
                    await self._update_session(session_id, {"booking_context": context})
                    return {
                        "reply": "No special exhibitions currently. We'll proceed with your selected ticket type.\n\n👤 What's the name for the booking?",
                    }
            else:
                context["state"] = "collect_name"
                await self._update_session(session_id, {"booking_context": context})
                return {
                    "reply": f"Category: **{category.replace('_', ' ').title()}** ✓\n\n👤 What name should I put on the booking?",
                }

        return {
            "reply": "Please select a visitor category:\n\n1. Adult\n2. Child\n3. Student\n4. Senior\n5. Foreign Tourist",
        }

    async def _handle_exhibition(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower().strip()
        exhibitions = await TicketService.get_exhibitions()

        selected = None
        # Try number selection
        try:
            idx = int(msg_lower) - 1
            if 0 <= idx < len(exhibitions):
                selected = exhibitions[idx]
        except (ValueError, TypeError):
            pass

        # Try name matching
        if not selected:
            for ex in exhibitions:
                if ex["name"].lower() in msg_lower or msg_lower in ex["name"].lower():
                    selected = ex
                    break

        if selected:
            context["exhibition_id"] = selected["exhibition_id"]
            context["exhibition_name"] = selected["name"]

            # If show type, ask for show time
            if context.get("ticket_type") == "show" and selected.get("show_times"):
                context["state"] = "select_show_time"
                await self._update_session(session_id, {"booking_context": context})

                reply = f"🎭 **{selected['name']}** selected!\n\n⏰ Available show times:\n\n"
                for i, time in enumerate(selected["show_times"], 1):
                    reply += f"{i}. {time}\n"
                reply += "\nWhich show time works for you?"
                return {"reply": reply}
            else:
                context["state"] = "collect_name"
                await self._update_session(session_id, {"booking_context": context})
                return {
                    "reply": f"🎨 **{selected['name']}** selected! ✓\n\n👤 What name should I put on the booking?",
                }

        return {
            "reply": "I couldn't find that exhibition. Please select by number from the list above, or type the exhibition name.",
        }

    async def _handle_show_time(self, message, entities, context, session_id, user_id):
        msg_lower = message.strip()

        exhibitions = await TicketService.get_exhibitions()
        exhibition = None
        for ex in exhibitions:
            if ex["exhibition_id"] == context.get("exhibition_id"):
                exhibition = ex
                break

        show_times = exhibition.get("show_times", []) if exhibition else []

        selected_time = None
        try:
            idx = int(msg_lower) - 1
            if 0 <= idx < len(show_times):
                selected_time = show_times[idx]
        except (ValueError, TypeError):
            if msg_lower in show_times:
                selected_time = msg_lower

        if selected_time:
            context["show_time"] = selected_time
            context["state"] = "collect_name"
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": f"⏰ Show time: **{selected_time}** ✓\n\n👤 What name should I put on the booking?",
            }

        return {"reply": "Please select a valid show time from the list above."}

    async def _handle_name(self, message, entities, context, session_id, user_id):
        name = entities.get("name") or message.strip()

        if name and len(name) >= 2:
            context["visitor_name"] = name
            context["state"] = "collect_email"
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": f"👤 Name: **{name}** ✓\n\n📧 What's your email address? (for ticket confirmation)",
            }

        return {"reply": "Please provide a valid name for the booking."}

    async def _handle_email(self, message, entities, context, session_id, user_id):
        email = entities.get("email") or message.strip()

        # Basic email validation
        if email and '@' in email and '.' in email:
            context["visitor_email"] = email
            context["state"] = "collect_phone"
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": f"📧 Email: **{email}** ✓\n\n📱 Phone number? (optional - type 'skip' to skip)",
            }

        return {"reply": "Please provide a valid email address (e.g., name@example.com)"}

    async def _handle_phone(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower().strip()

        if msg_lower in ['skip', 'no', 'none', 'na', 'n/a']:
            context["visitor_phone"] = None
        else:
            phone = entities.get("phone") or message.strip()
            context["visitor_phone"] = phone

        context["state"] = "confirm_booking"
        await self._update_session(session_id, {"booking_context": context})

        # Generate booking summary
        return await self._show_booking_summary(context, session_id)

    async def _show_booking_summary(self, context, session_id):
        """Show booking summary for confirmation."""
        # Calculate price
        exhibition_price = 0.0
        exhibition_name = context.get("exhibition_name", "")
        if context.get("exhibition_id"):
            exhibition = await TicketService.get_exhibition(context["exhibition_id"])
            if exhibition:
                exhibition_price = exhibition.get("ticket_price", 0)
                exhibition_name = exhibition.get("name", "")

        pricing = TicketService.calculate_price(
            ticket_type=context.get("ticket_type", "gate_entry"),
            visitor_category=context.get("visitor_category", "adult"),
            num_tickets=context.get("num_tickets", 1),
            exhibition_price=exhibition_price,
        )

        type_labels = {
            "gate_entry": "Gate Entry",
            "exhibition": "Exhibition",
            "show": "Show",
            "guided_tour": "Guided Tour",
            "combo": "Combo Package",
        }

        discount_line = f"🏷️ **Discount**: -₹{pricing['discount_applied']}\n" if pricing['discount_applied'] > 0 else ""
        exhibition_line = f"🎨 **Exhibition**: {exhibition_name}\n" if exhibition_name else ""
        show_line = f"⏰ **Show Time**: {context.get('show_time')}\n" if context.get('show_time') else ""

        summary = f"""📋 **Booking Summary**
━━━━━━━━━━━━━━━━━━━━━
🎭 **Ticket Type**: {type_labels.get(context.get('ticket_type'), context.get('ticket_type'))}
📅 **Visit Date**: {context.get('visit_date')}
👤 **Name**: {context.get('visitor_name')}
📧 **Email**: {context.get('visitor_email')}
🏷️ **Category**: {context.get('visitor_category', 'adult').replace('_', ' ').title()}
🔢 **Tickets**: {context.get('num_tickets', 1)}
💰 **Price/ticket**: ₹{pricing['unit_price']}
{discount_line}{exhibition_line}{show_line}💳 **Total Amount**: ₹{pricing['total_price']}
━━━━━━━━━━━━━━━━━━━━━

✅ **Confirm this booking?** (yes/no)"""

        return {
            "reply": summary,
            "action": "confirm_booking",
            "data": {"pricing": pricing},
        }

    async def _handle_confirmation(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower().strip()

        if any(word in msg_lower for word in ['yes', 'confirm', 'proceed', 'book', 'ok', 'sure', 'y']):
            # Create booking
            booking = await TicketService.create_booking(
                booking_data=context,
                user_id=user_id,
                session_id=session_id,
            )

            if booking:
                booking_id = booking["booking_id"]

                # Create payment session
                payment_result = await PaymentService.create_payment_session(
                    booking_id=booking_id,
                    amount=booking["total_price"],
                    customer_email=context.get("visitor_email", ""),
                    description=f"Museum Ticket - {context.get('ticket_type', 'gate_entry')}",
                )

                context["state"] = "payment"
                context["booking_id"] = booking_id
                await self._update_session(session_id, {"booking_context": context})

                payment_url = payment_result.get("payment_url", "#")

                reply = f"""✅ **Booking Created!**

📋 **Booking ID**: `{booking_id}`
💳 **Total**: ₹{booking['total_price']}

🔗 **Complete Payment**: [Click here to pay]({payment_url})

⏰ Please complete payment within 15 minutes.

After payment, type **'paid'** or **'confirm payment'** to finalize your ticket.

Or type **'cancel'** to cancel this booking."""

                return {
                    "reply": reply,
                    "action": "payment_pending",
                    "data": {
                        "booking_id": booking_id,
                        "payment_url": payment_url,
                        "amount": booking["total_price"],
                    },
                }
            else:
                return {"reply": "❌ Sorry, there was an error creating your booking. Please try again."}

        elif any(word in msg_lower for word in ['no', 'cancel', 'n', 'nope']):
            context["state"] = "greeting"
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": "Booking cancelled. No worries! 😊\n\nIs there anything else I can help you with?",
                "action": "cancelled",
            }
        else:
            return {"reply": "Please confirm: Type **'yes'** to confirm or **'no'** to cancel."}

    async def _handle_payment(self, message, entities, context, session_id, user_id):
        msg_lower = message.lower().strip()

        if any(word in msg_lower for word in ['paid', 'done', 'completed', 'confirm payment', 'payment done']):
            booking_id = context.get("booking_id")
            if booking_id:
                # Simulate payment success (in production, this comes from webhook)
                result = await PaymentService.handle_payment_success(booking_id)

                if result.get("success"):
                    context["state"] = "greeting"
                    await self._update_session(session_id, {"booking_context": context})

                    qr_code = result.get("qr_code", "")
                    reply = f"""🎉 **Payment Confirmed!**

✅ Your ticket is ready!

📋 **Booking ID**: `{booking_id}`
📅 **Visit Date**: {context.get('visit_date')}
👤 **Visitor**: {context.get('visitor_name')}
🔢 **Tickets**: {context.get('num_tickets')}

🎫 Your QR code ticket has been generated. Show it at the museum entrance.

🏛️ **Enjoy your visit to the National Heritage Museum!**

Is there anything else I can help you with?"""

                    return {
                        "reply": reply,
                        "action": "ticket_confirmed",
                        "data": {
                            "booking_id": booking_id,
                            "qr_code": qr_code,
                        },
                    }
                else:
                    return {
                        "reply": f"⚠️ Payment verification issue: {result.get('error', 'Unknown error')}. Please try again or contact support.",
                    }

        if any(word in msg_lower for word in ['cancel']):
            booking_id = context.get("booking_id")
            if booking_id:
                await TicketService.cancel_booking(booking_id)
            context["state"] = "greeting"
            await self._update_session(session_id, {"booking_context": context})
            return {
                "reply": "Booking cancelled and payment voided. Is there anything else I can help with?",
                "action": "cancelled",
            }

        return {
            "reply": f"⏳ Waiting for payment confirmation.\n\n📋 Booking ID: `{context.get('booking_id')}`\n\nAfter completing payment, type **'paid'** to get your QR ticket.\nOr type **'cancel'** to cancel.",
        }

    async def _handle_booking_lookup(self, message, session_id):
        """Handle booking lookup requests."""
        # Try to extract booking ID
        import re
        booking_ids = re.findall(r'[A-Z0-9]{8,12}', message.upper())

        if booking_ids:
            booking = await TicketService.get_booking(booking_ids[0])
            if booking:
                reply = f"""📋 **Booking Found!**

🆔 **Booking ID**: {booking['booking_id']}
🎭 **Type**: {booking.get('ticket_type', 'N/A')}
📅 **Visit Date**: {booking.get('visit_date', 'N/A')}
👤 **Visitor**: {booking.get('visitor_name', 'N/A')}
🔢 **Tickets**: {booking.get('num_tickets', 'N/A')}
💰 **Total**: ₹{booking.get('total_price', 0)}
📊 **Status**: {booking.get('status', 'N/A').upper()}
💳 **Payment**: {booking.get('payment_status', 'N/A').upper()}"""
                return {"reply": reply, "data": booking}
            else:
                return {"reply": "❌ No booking found with that ID. Please check and try again."}

        return {"reply": "Please provide your Booking ID to look it up (e.g., ABC12345678)."}


# Singleton agent instance
museum_agent = MuseumAgent()
