import os
import sys
import django
import asyncio
from websockets.client import connect
import json
import random
import string
import time

from django.contrib.auth import get_user_model
from django.test import Client
from asgiref.sync import sync_to_async

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'advisingwebsite.settings')
django.setup()

from advisingwebsiteapp.models import Chat, ChatMember

User = get_user_model()

BASE_URL = "ws://localhost:8000"
EMAIL_PREFIX = "user"
EMAIL_DOMAIN = "@example.com"
PASSWORD = "TestPass123!"

# Globals (reset per batch)
start_event = None
connected_users = 0
connect_lock = asyncio.Lock()
CHAT_ID = None


def create_users(total_users):
    users = []
    for i in range(1, total_users + 1):
        email = f"{EMAIL_PREFIX}{i}{EMAIL_DOMAIN}"
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_password(PASSWORD)
            user.first_name = f"User{i}"
            user.last_name = "Test"
            user.is_student = True
            user.save()
        users.append(user)
    return users


def create_chat_with_users(users):
    global CHAT_ID
    chat = Chat.objects.create(chat_name="Stress Test Chat")
    for user in users:
        ChatMember.objects.get_or_create(user=user, chat=chat)
    CHAT_ID = str(chat.id)
    print(f"✅ Created Chat ID: {CHAT_ID} with {len(users)} members")
    return chat


def get_session_cookie(email, password):
    client = Client()
    response = client.post("/login/", {
        "email": email,
        "password": password
    }, follow=True)

    if response.status_code != 200:
        print(f"[{email}] ❌ Login failed with status {response.status_code}")
        print("Response content:")
        print(response.content.decode())
        return None

    cookie = client.cookies.get("sessionid")
    if not cookie:
        print(f"[{email}] ❌ Login succeeded but no sessionid cookie found.")
        return None

    return cookie.value


async def simulate_user(email, total_users, message_count=5):
    global connected_users
    timings = []
    total_received = 0
    expected_total = total_users * message_count

    try:
        sessionid = await sync_to_async(get_session_cookie)(email, PASSWORD)
        if sessionid is None:
            print(f"[{email}] ⚠️ Skipping user due to missing sessionid.")
            return

        uri = f"{BASE_URL}/ws/chat/{CHAT_ID}/"
        headers = [("Cookie", f"sessionid={sessionid}")]

        async with connect(uri, extra_headers=headers) as websocket:
            await websocket.send(json.dumps({
                "command": "fetch_messages",
                "chat_id": CHAT_ID
            }))
            await websocket.recv()

            async with connect_lock:
                connected_users += 1
                if connected_users == total_users:
                    print(f"✅ All {total_users} clients connected. Broadcasting start signal...")
                    start_event.set()

            await start_event.wait()

            outstanding_messages = {}

            async def receive():
                nonlocal total_received
                while True:
                    try:
                        data = await websocket.recv()
                        response = json.loads(data)
                        if response.get("command") == "new_message":
                            total_received += 1
                            msg_content = response["message"]["content"]
                            msg_id = msg_content.split("::")[0]
                            if msg_id in outstanding_messages:
                                send_time = outstanding_messages.pop(msg_id)
                                delay = time.time() - send_time
                                timings.append(delay)
                                if delay > 3:
                                    print(f"[{email}] ⚠️ Slow response: {delay:.2f}s for message ID {msg_id}")
                    except Exception:
                        break

            receiver = asyncio.create_task(receive())

            await asyncio.sleep(random.uniform(3, 10))  # Wait before sending messages

            sent_messages = 0
            for _ in range(message_count):
                msg_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                message = f"{msg_id}::{email}: Hello there!"
                outstanding_messages[msg_id] = time.time()

                await websocket.send(json.dumps({
                    "command": "new_message",
                    "message": message,
                    "from": email,
                    "chat_id": CHAT_ID
                }))
                sent_messages += 1
                await asyncio.sleep(random.uniform(3, 10))

            print(f"[{email}] 📤 Sent {sent_messages}/{message_count} messages.")

            # ✅ Wait for all expected messages
            timeout = 15
            start = time.time()
            while (total_received < expected_total) and (time.time() - start < timeout):
                await asyncio.sleep(0.1)

            await asyncio.sleep(1)  # Small grace period

            receiver.cancel()
            try:
                await receiver
            except asyncio.CancelledError:
                pass

            try:
                await websocket.close()
            except Exception as e:
                print(f"[{email}] ⚠️ Error closing socket: {e}")

            if total_received < expected_total:
                print(f"[{email}] ⚠️ Received only {total_received}/{expected_total} messages.")
            else:
                print(f"[{email}] ✅ Received all {expected_total} messages.")

            if timings:
                avg = sum(timings) / len(timings)
                print(f"[{email}] ✅ Avg: {avg:.2f}s | Min: {min(timings):.2f}s | Max: {max(timings):.2f}s")
            else:
                print(f"[{email}] ❌ No response timings collected.")

    except Exception as e:
        print(f"[{email}] ❌ Error: {e}")


async def run_stress_test(users, message_count):
    emails = [user.email for user in users]
    await asyncio.gather(*(simulate_user(email, len(users), message_count) for email in emails))


def reset_state():
    global connected_users, start_event
    connected_users = 0
    start_event = asyncio.Event()


if __name__ == "__main__":
    for batch_size in [10, 25, 40]:
        print(f"\n🚀 Running stress test with {batch_size} users...")
        reset_state()
        users = create_users(batch_size)
        create_chat_with_users(users)
        asyncio.run(run_stress_test(users, message_count=5))
        print(f"✅ Finished batch of {batch_size} users.\n")
        time.sleep(5)  # Cooldown between batches
