import os
from django.contrib.auth import get_user_model
from channels.testing import ChannelsLiveServerTestCase
from django.test import override_settings
import pytest
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from advisingwebsiteapp.models import User
import time
from django.db import connection
from advisingwebsiteapp.models import Chat, ChatMember, Message
from selenium.webdriver.common.keys import Keys

User = get_user_model()

user1 = ""
user2 = ""
user3 = ""
user4 = ""

@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("localhost", 6379)],
            },
        },
    }
)

@pytest.mark.django_db
class SingleUserTesting(ChannelsLiveServerTestCase):
    serve_static = True
    
    def setUp(self):
        self.selenium = WebDriver()
        self.selenium.implicitly_wait(10)

    def tearDown(self):
        self.selenium.delete_all_cookies()
        self.selenium.quit()

    def login_and_open_home(self):
        user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass",
            first_name="User",
            last_name="One",
            is_student=True,
            is_advisor=False,
            student_id=102010
        )
        user2 = User.objects.create_user(
            email="user2@example.com",
            password="testpass",
            first_name="User",
            last_name="Two",
            is_student=True,
            is_advisor=True,
            student_id=102011
        )
        
        self.selenium.get(f'{self.live_server_url}/login/')
        self.selenium.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium.find_element(By.NAME, 'password').send_keys('testpass')
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        time.sleep(1)

        self.selenium.get(f'{self.live_server_url}/chat/')
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, 'addchat'))
        )

    def test_create_chat_and_see_it(self):
        self.login_and_open_home()

        self.selenium.find_element(By.ID, 'addchat').click()

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'chatPopup'))
        )

        select2_container = self.selenium.find_element(By.CSS_SELECTOR, '#chatParticipants + .select2-container')
        select2_container.click()

        search_input = WebDriverWait(self.selenium, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.select2-container .select2-search__field'))
        )
        search_input.send_keys('User Two')

        options = WebDriverWait(self.selenium, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("No valid user option found in Select2 dropdown")

        WebDriverWait(self.selenium, 3).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, '.select2-results'))
        )

        submit_button = self.selenium.find_element(By.CSS_SELECTOR, '#newChatForm button[type="submit"]')
        submit_button.click()

        WebDriverWait(self.selenium, 5).until(
            EC.invisibility_of_element_located((By.ID, 'chatPopup'))
        )

        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#chats ul li'))
        )

        chat_name = "User Two"
        chat_elements = self.selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        found_chat = False
        for chat in chat_elements:
            chat_name_element = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in chat_name_element.text:
                found_chat = True
                break

        if not found_chat:
            self.fail(f"Chat with name '{chat_name}' not found in the chat list.")
        else:
            print(f"Chat with name '{chat_name}' successfully found in the chat list.")

    def test_create_chat_enter_it_and_type_a_message(self):
        self.test_create_chat_and_see_it()

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#chats ul li .meta .name'),
                "User Two"
            )
        )

        chat_name = "User Two"
        chat_elements = self.selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in name_elem.text:
                chat.click()
                break
        else:
            self.fail(f"Chat with name '{chat_name}' not found in the sidebar to click.")

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'chat-name-display'))
        )

        chat_header = self.selenium.find_element(By.ID, 'chat-name-display')
        self.assertIn(chat_name, chat_header.text)

        message_text = "Hello from Selenium!"
        message_input = self.selenium.find_element(By.ID, 'chat-message-input')
        message_input.send_keys(message_text)

        send_button = self.selenium.find_element(By.ID, 'chat-message-submit')
        send_button.click()

        WebDriverWait(self.selenium, 5).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#chat-log li.sent p'),
                message_text
            )
        )

        messages = self.selenium.find_elements(By.CSS_SELECTOR, '#chat-log li.sent p')
        self.assertTrue(
            any(message_text in msg.get_attribute("innerText") for msg in messages),
            f"Message '{message_text}' not found in chat log."
        )
    
    def test_create_chat_and_delete_it(self):
        self.test_create_chat_and_see_it()

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#chats ul li .meta .name'),
                "User Two"
            )
        )

        self.selenium.find_element(By.ID, 'delete-chat').click()

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'delete-chat-popup'))
        )

        select2_container = self.selenium.find_element(By.CSS_SELECTOR, '#chatsToDelete + .select2-container')
        select2_container.click()

        search_input = WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.select2-container--open .select2-search__field'))
        )

        search_input.click()
        search_input.send_keys('User Two')

        options = WebDriverWait(self.selenium, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("No valid user option found in Select2 dropdown")

        submit_button = self.selenium.find_element(By.CSS_SELECTOR, '#deleteChatForm button[type="submit"]')
        submit_button.click()

        WebDriverWait(self.selenium, 5).until(
            EC.invisibility_of_element_located((By.ID, 'delete-chat-popup'))
        )

        chat_name = "User Two"
        chat_elements = self.selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        found_chat = any(
            chat_name in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
            for chat in chat_elements
        )

        if not found_chat:
            print(f"Chat with name '{chat_name}' successfully deleted from the chat list.")
        else:
            self.fail(f"Chat with name '{chat_name}' found in the chat list and was not deleted.")
    
    def test_create_chat_and_delete_it_while_in_chat(self):
        self.test_create_chat_and_see_it()

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#chats ul li .meta .name'),
                "User Two"
            )
        )

        chat_name = "User Two"
        chat_elements = self.selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in name_elem.text:
                chat.click()
                break
        else:
            self.fail(f"Chat with name '{chat_name}' not found in the sidebar to click.")

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'chat-name-display'))
        )

        chat_header = self.selenium.find_element(By.ID, 'chat-name-display')
        self.assertIn(chat_name, chat_header.text)

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#chats ul li .meta .name'),
                "User Two"
            )
        )

        self.selenium.find_element(By.ID, 'delete-chat').click()

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'delete-chat-popup'))
        )

        select2_container = self.selenium.find_element(By.CSS_SELECTOR, '#chatsToDelete + .select2-container')
        select2_container.click()

        search_input = WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.select2-container--open .select2-search__field'))
        )

        search_input.click()
        search_input.send_keys('User Two')

        options = WebDriverWait(self.selenium, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("No valid user option found in Select2 dropdown")

        submit_button = self.selenium.find_element(By.CSS_SELECTOR, '#deleteChatForm button[type="submit"]')
        submit_button.click()

        WebDriverWait(self.selenium, 5).until(
            EC.invisibility_of_element_located((By.ID, 'delete-chat-popup'))
        )

        self.assertTrue(
            self.selenium.current_url.endswith('/chat/'),
            f"Expected to be redirected to /chat/, but got {self.selenium.current_url}"
        )

        chat_name = "User Two"
        chat_elements = self.selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        found_chat = any(
            chat_name in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
            for chat in chat_elements
        )

        if not found_chat:
            print(f"Chat with name '{chat_name}' successfully deleted from the chat list.")
        else:
            self.fail(f"Chat with name '{chat_name}' found in the chat list and was not deleted.")
    
    def test_search_chats(self):
        user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass",
            first_name="User",
            last_name="One",
            is_student=True,
            is_advisor=False,
            student_id=102010
        )


        user2 = User.objects.create_user(
            email="user2@example.com",
            password="testpass",
            first_name="User",
            last_name="Two",
            is_student=True,
            is_advisor=True,
            student_id=102011
        )


        user3 = User.objects.create_user(
            email="user3@example.com",
            password="testpass",
            first_name="User",
            last_name="Three",
            is_student=True,
            is_advisor=True,
            student_id=102012
        )
        
        user4 = User.objects.create_user(
            email="user4@example.com",
            password="testpass",
            first_name="User",
            last_name="Four",
            is_student=False,
            is_advisor=True,
            student_id=102013
        )

        chat1 = Chat.objects.create(
            chat_name="User One, User Two"
        )
        chat2 = Chat.objects.create(
            chat_name="User One, User Three"
        )
        chat3 = Chat.objects.create(
            chat_name="User One, User Four"
        )

        ChatMember.objects.create(user=user1, chat=chat1)
        ChatMember.objects.create(user=user2, chat=chat1)
        ChatMember.objects.create(user=user1, chat=chat2)
        ChatMember.objects.create(user=user3, chat=chat2)
        ChatMember.objects.create(user=user1, chat=chat3)
        ChatMember.objects.create(user=user4, chat=chat3)

        self.selenium.get(f'{self.live_server_url}/login/')
        self.selenium.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium.find_element(By.NAME, 'password').send_keys('testpass')
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()

        self.selenium.get(f'{self.live_server_url}/chat/')

        # Wait for search bar to appear and input the search query
        search_input = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, "search-input"))
        )
        search_input.clear()
        search_input.send_keys("Three")

        self.selenium.execute_script("""
            const waitForSocket = (callback) => {
                const socket = chatSocket;
                const check = () => {
                    if (socket.readyState === 1) {
                        callback();
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            };

            waitForSocket(() => {
                const input = document.getElementById('search-input');
                const event = new KeyboardEvent('keyup', {
                    bubbles: true,
                    cancelable: true,
                    key: 'e',
                    code: 'KeyE',
                    keyCode: 69
                });
                input.dispatchEvent(event);
            });
        """)

        time.sleep(2)

        # Wait a bit for filtering effect to reflect (adjust if your app has debounce)
        WebDriverWait(self.selenium, 2).until(
            lambda driver: any("Three" in chat.text for chat in driver.find_elements(By.CSS_SELECTOR, "#chats ul li .meta .name"))
        )

        # Check only matching chat(s) are visible
        visible_chats = self.selenium.find_elements(By.CSS_SELECTOR, "#chats ul li")
        for chat in visible_chats:
            name = chat.find_element(By.CSS_SELECTOR, ".meta .name").text
            self.assertIn("Three", name)

    def test_search_chats_in_active_chat(self):
        self.test_search_chats()

        chat_name = "User Three"
        chat_elements = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#chats ul li'))
        )
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in name_elem.text:
                self.selenium.execute_script("arguments[0].click();", chat)
                break
        else:
            self.fail(f"Chat with name '{chat_name}' not found in the sidebar to click.")

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'chat-name-display'))
        )

        chat_header = self.selenium.find_element(By.ID, 'chat-name-display')
        self.assertIn(chat_name, chat_header.text)

        # Wait for search bar to appear and input the search query
        search_input = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, "search-input"))
        )
        search_input.clear()
        search_input.send_keys("Three")

        self.selenium.execute_script("""
            const waitForSocket = (callback) => {
                const socket = chatSocket;
                const check = () => {
                    if (socket.readyState === 1) {
                        callback();
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            };

            waitForSocket(() => {
                const input = document.getElementById('search-input');
                const event = new KeyboardEvent('keyup', {
                    bubbles: true,
                    cancelable: true,
                    key: 'e',
                    code: 'KeyE',
                    keyCode: 69
                });
                input.dispatchEvent(event);
            });
        """)

        time.sleep(2)

        # Wait a bit for filtering effect to reflect (adjust if your app has debounce)
        WebDriverWait(self.selenium, 2).until(
            lambda driver: any("Three" in chat.text for chat in driver.find_elements(By.CSS_SELECTOR, "#chats ul li .meta .name"))
        )

        # Check only matching chat(s) are visible
        visible_chats = self.selenium.find_elements(By.CSS_SELECTOR, "#chats ul li")
        for chat in visible_chats:
            name = chat.find_element(By.CSS_SELECTOR, ".meta .name").text
            self.assertIn("Three", name)

            classes = chat.get_attribute("class").split()
            self.assertIn("active", classes)

        search_input.clear()

        self.selenium.execute_script("""
            const waitForSocket = (callback) => {
                const socket = chatSocket;
                const check = () => {
                    if (socket.readyState === 1) {
                        callback();
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            };

            waitForSocket(() => {
                const input = document.getElementById('search-input');
                const event = new KeyboardEvent('keyup', {
                    bubbles: true,
                    cancelable: true,
                    key: 'e',
                    code: 'KeyE',
                    keyCode: 69
                });
                input.dispatchEvent(event);
            });
        """)

        time.sleep(2)

        # Checks that the first shown chat is the current active chat and it has the active class
        visible_chats = self.selenium.find_elements(By.CSS_SELECTOR, "#chats ul li")
        name = visible_chats[0].find_element(By.CSS_SELECTOR, ".meta .name").text
        self.assertIn("Three", name)

        classes = visible_chats[0].get_attribute("class").split()
        self.assertIn("active", classes)
    
    def test_load_messages_when_opening_chat(self):
        user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass",
            first_name="User",
            last_name="One",
            is_student=True,
            is_advisor=False,
            student_id=102010
        )


        user2 = User.objects.create_user(
            email="user2@example.com",
            password="testpass",
            first_name="User",
            last_name="Two",
            is_student=True,
            is_advisor=True,
            student_id=102011
        )

        chat1 = Chat.objects.create(
            chat_name="User One, User Two"
        )

        chatmember1 = ChatMember.objects.create(user=user1, chat=chat1)
        chatmember2 = ChatMember.objects.create(user=user2, chat=chat1)

        Message.objects.create(
            sent_by_member=chatmember1,
            chat=chat1,
            message_content='This is message number 1!'
        )
        Message.objects.create(
            sent_by_member=chatmember2,
            chat=chat1,
            message_content='This is message number 2!'
        )
        Message.objects.create(
            sent_by_member=chatmember1,
            chat=chat1,
            message_content='This is message number 3!'
        )

        self.selenium.get(f'{self.live_server_url}/login/')
        self.selenium.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium.find_element(By.NAME, 'password').send_keys('testpass')
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        time.sleep(1)

        self.selenium.get(f'{self.live_server_url}/chat/')
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, 'addchat'))
        )

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#chats ul li .meta .name'),
                "User Two"
            )
        )

        chat_name = "User Two"
        chat_elements = self.selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in name_elem.text:
                chat.click()
                break
        else:
            self.fail(f"Chat with name '{chat_name}' not found in the sidebar to click.")

        WebDriverWait(self.selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'chat-name-display'))
        )

        chat_header = self.selenium.find_element(By.ID, 'chat-name-display')
        self.assertIn(chat_name, chat_header.text)

        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#chat-log li p')),
            'This is message number 3!'
        )

        messages = self.selenium.find_elements(By.CSS_SELECTOR, '#chat-log li')
        for i in range(3):
            self.assertTrue(
                f"This is message number {i + 1}!" in messages[i].text,
                f"Message {i + 1} not found in chat log. {messages[i].text}"
            )
            
            # Check if the message has the 'sent' class
            message_classes = messages[i].get_attribute("class")
            if(i%2 == 0):
                self.assertTrue(
                    "sent" in message_classes,
                    f"Message {i + 1} does not have 'sent' class."
                )
            else:
                self.assertTrue(
                    "replies" in message_classes,
                    f"Message {i + 1} does not have 'sent' class."
                )

@pytest.mark.django_db
class MultiUserTesting(ChannelsLiveServerTestCase):
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass",
            first_name="User",
            last_name="One",
            is_student=True,
            is_advisor=True,
            student_id=102010
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="testpass",
            first_name="User",
            last_name="Two",
            is_student=True,
            is_advisor=True,
            student_id=102011
        )
        self.user3 = User.objects.create_user(
            email="user3@example.com",
            password="testpass",
            first_name="User",
            last_name="Three",
            is_student=True,
            is_advisor=True,
            student_id=102012
        )
        self.user4 = User.objects.create_user(
            email="user4@example.com",
            password="testpass",
            first_name="User",
            last_name="Four",
            is_student=True,
            is_advisor=True,
            student_id=102013
        )
        self.user5 = User.objects.create_user(
            email="user5@example.com",
            password="testpass",
            first_name="User",
            last_name="Five",
            is_student=True,
            is_advisor=True,
            student_id=102014
        )
        
        # Create a chat room and add users
        self.chat = Chat.objects.create(chat_name="Test Chat")
        ChatMember.objects.create(user=self.user1, chat=self.chat)
        ChatMember.objects.create(user=self.user2, chat=self.chat)

        self.chat2 = Chat.objects.create(chat_name="Test Chat 2")
        ChatMember.objects.create(user=self.user2, chat=self.chat2)
        ChatMember.objects.create(user=self.user3, chat=self.chat2)

        self.large_chat = Chat.objects.create(chat_name="Large Chat")
        ChatMember.objects.create(user=self.user1, chat=self.large_chat)
        ChatMember.objects.create(user=self.user2, chat=self.large_chat)
        ChatMember.objects.create(user=self.user3, chat=self.large_chat)
        ChatMember.objects.create(user=self.user4, chat=self.large_chat)
        ChatMember.objects.create(user=self.user5, chat=self.large_chat)

        # Set up Selenium instances for each user
        self.selenium1 = WebDriver()
        self.selenium1.implicitly_wait(20)
        self.selenium2 = WebDriver()
        self.selenium2.implicitly_wait(20)

    def tearDown(self):
        # Clean up Selenium instances
        self.selenium1.quit()
        self.selenium2.quit()
    
    def wait_for_chat_to_appear(self, selenium, chat_name, timeout=10):
        WebDriverWait(selenium, timeout).until(
            lambda driver: any(
                chat_name in el.text
                for el in driver.find_elements(By.CSS_SELECTOR, '#chats ul li .meta .name')
            )
        )
    
    def redirectToChat(self, selenium, chat_name):
        self.wait_for_chat_to_appear(selenium, chat_name)

        chat_elements = selenium.find_elements(By.CSS_SELECTOR, '#chats ul li')
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in name_elem.text:
                chat.click()
                break
        else:
            self.fail(f"Chat with name '{chat_name}' not found in the sidebar to click.")

        WebDriverWait(selenium, 5).until(
            EC.visibility_of_element_located((By.ID, 'chat-name-display'))
        )

        chat_header = selenium.find_element(By.ID, 'chat-name-display')
        self.assertIn(chat_name, chat_header.text)

        self.wait_for_chat_to_appear(selenium, chat_name)

    def test_message_received_by_second_user(self):
        # Log in as User 1
        self.selenium1.get(f'{self.live_server_url}/login/')
        self.selenium1.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium1.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Log in as User 2 in a different window or tab
        self.selenium2.get(f'{self.live_server_url}/login/')
        self.selenium2.find_element(By.NAME, 'email').send_keys('user2@example.com')
        self.selenium2.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium2.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.selenium1.implicitly_wait(2)
        self.selenium2.implicitly_wait(2)

        self.selenium1.get(f'{self.live_server_url}/chat/')
        self.selenium2.get(f'{self.live_server_url}/chat/')

        self.redirectToChat(self.selenium1, "Test Chat")
        self.redirectToChat(self.selenium2, "Test Chat")

        self.selenium1.implicitly_wait(3)
        self.selenium2.implicitly_wait(3)

        # User 1 sends a message
        message_input1 = self.selenium1.find_element(By.ID, 'chat-message-input')
        message_input1.send_keys("Hello User 2")
        send_button = self.selenium1.find_element(By.ID, 'chat-message-submit')
        send_button.click()

        # Wait for the message to appear in User 2's chat window
        WebDriverWait(self.selenium2, 10).until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#chat-log'), 'Hello User 2')
        )

        # Check that the message appears in User 2's window
        messages = self.selenium2.find_elements(By.CSS_SELECTOR, '#chat-log li.replies')
        self.assertTrue(any("Hello User 2" in msg.text for msg in messages))
    
    def test_ping_received_by_second_user_while_at_chat_home(self):
        # Log in as User 1
        self.selenium1.get(f'{self.live_server_url}/login/')
        self.selenium1.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium1.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Log in as User 2 in a different window or tab
        self.selenium2.get(f'{self.live_server_url}/login/')
        self.selenium2.find_element(By.NAME, 'email').send_keys('user2@example.com')
        self.selenium2.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium2.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.selenium1.implicitly_wait(2)
        self.selenium2.implicitly_wait(2)

        self.selenium1.get(f'{self.live_server_url}/chat/')
        self.selenium2.get(f'{self.live_server_url}/chat/')

        self.redirectToChat(self.selenium1, "Test Chat")

        self.selenium1.implicitly_wait(3)
        self.selenium2.implicitly_wait(3)

        # User 1 sends a message
        message_input1 = self.selenium1.find_element(By.ID, 'chat-message-input')
        message_input1.send_keys("Hello User 2")
        send_button = self.selenium1.find_element(By.ID, 'chat-message-submit')
        send_button.click()

        # Wait until the expected message appears in the correct chat preview
        WebDriverWait(self.selenium2, 20).until(lambda driver: any(
            "Hello User 2" in chat.find_element(By.CSS_SELECTOR, '.meta .preview').text
            for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            if "Test Chat" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
        ))

        # Now find the specific chat item again to assert the image class
        chat_elements = self.selenium2.find_elements(By.CSS_SELECTOR, '#chats ul li')
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if "Test Chat" == name_elem.text:
                preview = chat.find_element(By.CSS_SELECTOR, '.meta .preview')
                self.assertIn("Hello User 2", preview.text)

                img_elem = chat.find_element(By.CSS_SELECTOR, 'img')
                img_classes = img_elem.get_attribute("class").split()
                self.assertIn("newMessage", img_classes)
                break
        else:
            self.fail("Chat with name 'Test Chat 2' not found.")
    
    def test_ping_received_by_second_user_while_in_another_chat(self):
        # Log in as User 1
        self.selenium1.get(f'{self.live_server_url}/login/')
        self.selenium1.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium1.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Log in as User 2 in a different window or tab
        self.selenium2.get(f'{self.live_server_url}/login/')
        self.selenium2.find_element(By.NAME, 'email').send_keys('user2@example.com')
        self.selenium2.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium2.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.selenium1.implicitly_wait(2)
        self.selenium2.implicitly_wait(2)

        self.selenium1.get(f'{self.live_server_url}/chat/')
        self.selenium2.get(f'{self.live_server_url}/chat/')

        self.redirectToChat(self.selenium1, "Test Chat")
        self.redirectToChat(self.selenium2, "Test Chat 2")

        self.selenium1.implicitly_wait(3)
        self.selenium2.implicitly_wait(3)

        # User 1 sends a message
        message_input1 = self.selenium1.find_element(By.ID, 'chat-message-input')
        message_input1.send_keys("Hello User 2")
        send_button = self.selenium1.find_element(By.ID, 'chat-message-submit')
        send_button.click()

        # Wait until the expected message appears in the correct chat preview
        WebDriverWait(self.selenium2, 20).until(lambda driver: any(
            "Hello User 2" in chat.find_element(By.CSS_SELECTOR, '.meta .preview').text
            for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            if "Test Chat" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
        ))

        # Now find the specific chat item again to assert the image class
        chat_elements = self.selenium2.find_elements(By.CSS_SELECTOR, '#chats ul li')
        for chat in chat_elements:
            name_elem = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if "Test Chat" == name_elem.text:
                preview = chat.find_element(By.CSS_SELECTOR, '.meta .preview')
                self.assertIn("Hello User 2", preview.text)

                img_elem = chat.find_element(By.CSS_SELECTOR, 'img')
                img_classes = img_elem.get_attribute("class").split()
                self.assertIn("newMessage", img_classes)
                break
        else:
            self.fail("Chat with name 'Test Chat 2' not found.")
    
    def test_chat_added_to_sidebar_on_second_user_screen_while_second_user_at_chat_home(self):
        # Log in as User 1
        self.selenium1.get(f'{self.live_server_url}/login/')
        self.selenium1.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium1.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Log in as User 2 in a different window or tab
        self.selenium2.get(f'{self.live_server_url}/login/')
        self.selenium2.find_element(By.NAME, 'email').send_keys('user3@example.com')
        self.selenium2.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium2.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.selenium1.implicitly_wait(2)
        self.selenium2.implicitly_wait(2)

        self.selenium1.get(f'{self.live_server_url}/chat/')
        self.selenium2.get(f'{self.live_server_url}/chat/')

        self.selenium1.implicitly_wait(2)
        self.selenium2.implicitly_wait(2)

        self.selenium1.find_element(By.ID, 'addchat').click()

        WebDriverWait(self.selenium1, 5).until(
            EC.visibility_of_element_located((By.ID, 'chatPopup'))
        )

        select2_container = self.selenium1.find_element(By.CSS_SELECTOR, '#chatParticipants + .select2-container')
        select2_container.click()

        search_input = WebDriverWait(self.selenium1, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.select2-container .select2-search__field'))
        )
        search_input.send_keys('User Three')

        options = WebDriverWait(self.selenium1, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("No valid user option found in Select2 dropdown")

        WebDriverWait(self.selenium1, 3).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, '.select2-results'))
        )

        submit_button = self.selenium1.find_element(By.CSS_SELECTOR, '#newChatForm button[type="submit"]')
        submit_button.click()

        WebDriverWait(self.selenium2, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#chats ul li'))
        )

        chat_name = "User One"
        chat_elements = self.selenium2.find_elements(By.CSS_SELECTOR, '#chats ul li')
        found_chat = False
        for chat in chat_elements:
            chat_name_element = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name in chat_name_element.text:
                found_chat = True
                break

        if not found_chat:
            self.fail(f"Chat with name '{chat_name}' not found in the chat list.")
        else:
            print(f"Chat with name '{chat_name}' successfully found in the chat list.")
    
    def test_chat_added_to_sidebar_on_second_user_screen_while_user_in_another_chat(self):
        # Log in as User 1
        self.selenium1.get(f'{self.live_server_url}/login/')
        self.selenium1.find_element(By.NAME, 'email').send_keys('user1@example.com')
        self.selenium1.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Log in as User 2 in a different window or tab
        self.selenium2.get(f'{self.live_server_url}/login/')
        self.selenium2.find_element(By.NAME, 'email').send_keys('user3@example.com')
        self.selenium2.find_element(By.NAME, 'password').send_keys('testpass')
        self.selenium2.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.selenium1.implicitly_wait(2)
        self.selenium2.implicitly_wait(2)

        self.selenium1.get(f'{self.live_server_url}/chat/')
        self.selenium2.get(f'{self.live_server_url}/chat/')

        self.redirectToChat(self.selenium1, "Test Chat")
        self.redirectToChat(self.selenium2, "Test Chat 2")

        self.selenium1.implicitly_wait(3)
        self.selenium2.implicitly_wait(3)

        self.selenium1.find_element(By.ID, 'addchat').click()

        WebDriverWait(self.selenium1, 5).until(
            EC.visibility_of_element_located((By.ID, 'chatPopup'))
        )

        select2_container = self.selenium1.find_element(By.CSS_SELECTOR, '#chatParticipants + .select2-container')
        select2_container.click()

        search_input = WebDriverWait(self.selenium1, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.select2-container .select2-search__field'))
        )
        search_input.send_keys('User Three')

        options = WebDriverWait(self.selenium1, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("No valid user option found in Select2 dropdown")

        WebDriverWait(self.selenium1, 3).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, '.select2-results'))
        )

        submit_button = self.selenium1.find_element(By.CSS_SELECTOR, '#newChatForm button[type="submit"]')
        submit_button.click()

        # Wait until the expected message appears in the correct chat preview
        WebDriverWait(self.selenium2, 20).until(lambda driver: any(
            "No messages yet." in chat.find_element(By.CSS_SELECTOR, '.meta .preview').text
            for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            if "User One" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
        ))

        chat_name = "User One"
        chat_elements = self.selenium2.find_elements(By.CSS_SELECTOR, '#chats ul li')
        found_chat = False
        for chat in chat_elements:
            chat_name_element = chat.find_element(By.CSS_SELECTOR, '.meta .name')
            if chat_name == chat_name_element.text:
                found_chat = True
                break

        if not found_chat:
            self.fail(f"Chat with name '{chat_name}' not found in the chat list.")
        else:
            print(f"Chat with name '{chat_name}' successfully found in the chat list.")

    def test_full_implementation_message_system(self):
        self.selenium3 = WebDriver()
        self.selenium3.implicitly_wait(20)
        self.selenium4 = WebDriver()
        self.selenium4.implicitly_wait(20)
        self.selenium5 = WebDriver()
        self.selenium5.implicitly_wait(20)

        # Log in all 5 users
        users = [
            ('user1@example.com', self.selenium1),
            ('user2@example.com', self.selenium2),
            ('user3@example.com', self.selenium3),
            ('user4@example.com', self.selenium4),
            ('user5@example.com', self.selenium5)
        ]
        for email, browser in users:
            browser.get(f'{self.live_server_url}/login/')
            browser.find_element(By.NAME, 'email').send_keys(email)
            browser.find_element(By.NAME, 'password').send_keys('testpass')
            browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
            browser.implicitly_wait(2)
            browser.get(f'{self.live_server_url}/chat/')

        # User 1 and User 2 go to Large Chat
        self.redirectToChat(self.selenium1, "Large Chat")
        self.redirectToChat(self.selenium2, "Large Chat")

        # User 3 goes to Test Chat 2
        self.redirectToChat(self.selenium3, "Test Chat 2")

        # Users 4 and 5 will stay at chat home

        message_input1 = self.selenium1.find_element(By.ID, 'chat-message-input')
        message_input1.send_keys("Hello Users in Large Chat")
        self.selenium1.find_element(By.ID, 'chat-message-submit').click()

        #Check for message at User 2
        WebDriverWait(self.selenium2, 10).until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#chat-log'), 'Hello Users in Large Chat')
        )
        messages = self.selenium2.find_elements(By.CSS_SELECTOR, '#chat-log li.replies')
        self.assertTrue(any("Hello Users in Large Chat" in msg.text for msg in messages))

        #Check for ping at User 3 in a different chat
        WebDriverWait(self.selenium3, 20).until(lambda driver: any(
            "Hello Users in Large Chat" in chat.find_element(By.CSS_SELECTOR, '.meta .preview').text
            for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            if "Large Chat" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
        ))
        for chat in self.selenium3.find_elements(By.CSS_SELECTOR, '#chats ul li'):
            if chat.find_element(By.CSS_SELECTOR, '.meta .name').text == "Large Chat":
                self.assertIn("Hello Users in Large Chat", chat.find_element(By.CSS_SELECTOR, '.meta .preview').text)
                self.assertIn("newMessage", chat.find_element(By.CSS_SELECTOR, 'img').get_attribute("class").split())
                break
        else:
            self.fail("Chat 'Large Chat' not found for User 4.")

        # Check for ping at User 4 at the chat home
        WebDriverWait(self.selenium4, 20).until(lambda driver: any(
            "Hello Users in Large Chat" in chat.find_element(By.CSS_SELECTOR, '.meta .preview').text
            for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            if "Large Chat" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
        ))
        for chat in self.selenium4.find_elements(By.CSS_SELECTOR, '#chats ul li'):
            if chat.find_element(By.CSS_SELECTOR, '.meta .name').text == "Large Chat":
                self.assertIn("Hello Users in Large Chat", chat.find_element(By.CSS_SELECTOR, '.meta .preview').text)
                self.assertIn("newMessage", chat.find_element(By.CSS_SELECTOR, 'img').get_attribute("class").split())
                break
        else:
            self.fail("Chat 'Large Chat' not found for User 4.")

        # Check for new chat created by User 1 in User 5's sidebar
        self.selenium1.find_element(By.ID, 'addchat').click()
        WebDriverWait(self.selenium1, 5).until(EC.visibility_of_element_located((By.ID, 'chatPopup')))
        self.selenium1.find_element(By.CSS_SELECTOR, '#chatParticipants + .select2-container').click()
        search_input = WebDriverWait(self.selenium1, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.select2-search__field'))
        )
        search_input.send_keys('User Five')
        options = WebDriverWait(self.selenium1, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("User Five not found in Select2 dropdown.")

        self.selenium1.find_element(By.CSS_SELECTOR, '#newChatForm button[type="submit"]').click()

        WebDriverWait(self.selenium5, 20).until(
            lambda driver: any(
                "User One" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
                for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            )
        )
        found = any(
            "User One" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
            for chat in self.selenium5.find_elements(By.CSS_SELECTOR, '#chats ul li')
        )
        self.assertTrue(found, "User Five did not see new chat added by User One.")

        # Check for new chat created by User 4 in User 1's sidebar
        self.selenium4.find_element(By.ID, 'addchat').click()
        WebDriverWait(self.selenium4, 5).until(EC.visibility_of_element_located((By.ID, 'chatPopup')))
        self.selenium4.find_element(By.CSS_SELECTOR, '#chatParticipants + .select2-container').click()
        search_input = WebDriverWait(self.selenium4, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.select2-search__field'))
        )
        search_input.send_keys('User One')
        options = WebDriverWait(self.selenium4, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select2-results__option'))
        )
        for option in options:
            if "no results" not in option.text.lower():
                option.click()
                break
        else:
            self.fail("User One not found in Select2 dropdown.")

        self.selenium4.find_element(By.CSS_SELECTOR, '#newChatForm button[type="submit"]').click()

        WebDriverWait(self.selenium1, 20).until(
            lambda driver: any(
                "User Four" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
                for chat in driver.find_elements(By.CSS_SELECTOR, '#chats ul li')
            )
        )
        found = any(
            "User One" in chat.find_element(By.CSS_SELECTOR, '.meta .name').text
            for chat in self.selenium5.find_elements(By.CSS_SELECTOR, '#chats ul li')
        )
        self.assertTrue(found, "User One did not see new chat added by User Four.")

        self.selenium3.quit()
        self.selenium4.quit()
        self.selenium5.quit()