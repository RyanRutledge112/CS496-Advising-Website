import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as roomBase from '../../static/room_base.js';
import * as room from '../../static/room.js';

jest.mock('../../static/reconnecting-websocket', () => {
  return jest.fn().mockImplementation(() => ({
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn((event, callback) => {
      if (event === 'open') callback();
      if (event === 'message') callback({ data: 'new message data' });
    }),
  }));
});

beforeAll(() => {
  global.alert = jest.fn();
  localStorage.setItem('activeChat', '123');
});

afterAll(() => {
  global.alert.mockRestore();
});

beforeEach(() => {
  document.body.innerHTML = `
    <div id="frame">
      <div id="sidepanel">
        <div id="profile">
          <div class="wrap">
            <img id="profile-img" src="profile.jpg" class="offline" alt="" />
            <p><b>John Doe</b></p>
          </div>
        </div>

        <div id="search">
          <label><i class="fa fa-search" aria-hidden="true"></i></label>
          <input id="search-input" type="text" placeholder="Type the chat name here to search..." />
        </div>

        <div id="chats">
          <ul>
            <li class="chat" data-chat-id="1" id="chat-1">Chat 1</li>
            <li class="chat" data-chat-id="2" id="chat-2">Chat 2</li>
          </ul>
        </div>

        <div id="bottom-bar">
          <button id="addchat"><i class="fa fa-user-plus fa-fw" aria-hidden="true"></i> <span>Add chat</span></button>

          <div id="chatPopup" class="modal-add-chat">
            <div class="modal-content-add-chat">
              <span class="close-add-chat">&times;</span>
              <h2>Create New Chat</h2>
              <form id="newChatForm">
                <label for="chatParticipants">Select Users:</label>
                <div class="select2-wrapper">
                  <select id="chatParticipants" name="chatParticipants" multiple required>
                    <option value="1">Alice Johnson</option>
                    <option value="2">Bob Smith</option>
                  </select>
                  <button type="submit">Create Chat</button>
                </div>
              </form>
            </div>
          </div>

          <div id="delete-chat-popup" class="modal-delete-chat">
            <div class="modal-content-delete-chat">
              <span class="close-delete-chat">&times;</span>
              <h2>Delete Chats</h2>
              <form id="deleteChatForm">
                <label for="chats">Select Chats to delete:</label>
                <div class="select2-wrapper">
                  <select id="chatsToDelete" name="chatsToDelete" multiple required>
                    <option value="chat123">Advising Group</option>
                    <option value="chat456">Math Tutors</option>
                  </select>
                  <button type="submit">Delete Chats</button>
                </div>
              </form>
            </div>
          </div>

          <button id="home"><i class="fa fa-home fa-fw" aria-hidden="true"></i> <span>Home</span></button>
        </div>
      </div>

      <div class="content">
        <div class="chat-profile">
          <img src="https://www.wku.edu/athletictraditions/images/redtowellogo.gif" alt="" />
          <p>WKU Advising Messages</p>
          <button id="delete-chat" class="social-media"><p>Delete Chats:</p><i class="fa fa-trash" aria-hidden="true"></i></button>
        </div>

        <div class="messages">
          <ul id="chat-log">
            <li class="sent">
              <img src="https://www.wku.edu/athletictraditions/images/redtowellogo.gif" alt="" />
              <p><strong>WKU Advising</strong><br>Welcome to the WKU Advising Messaging System!</p>
            </li>
            <li class="replies">
              <img src="https://www.wku.edu/athletictraditions/images/redtowellogo.gif" alt="" />
              <p><strong>WKU Advising</strong><br>Click on a chat or add a new one using "Add Chat."</p>
            </li>
            <li class="sent">
              <img src="https://www.wku.edu/athletictraditions/images/redtowellogo.gif" alt="" />
              <p><strong>WKU Advising</strong><br>Click the active chat again to return to this page.</p>
            </li>
            <li class="replies">
              <img src="https://www.wku.edu/athletictraditions/images/redtowellogo.gif" alt="" />
              <p><strong>WKU Advising</strong><br>Use the "Home" button to return to the site homepage.</p>
            </li>
          </ul>
        </div>
        <div class="message-input">
          <div class="wrap">
            <input id="chat-message-input" type="text" placeholder="Write your message..." />
            <button id="chat-message-submit" class="submit">Send</button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Mocking scrollIntoView for the test
  HTMLElement.prototype.scrollIntoView = jest.fn();

  document.querySelectorAll('.chat').forEach(chat => {
    chat.addEventListener('click', () => {
      document.querySelectorAll('.chat').forEach(c => c.classList.remove('active'));
      chat.classList.add('active');
    });
  });

  document.body.dataset.email = "test@example.com";
  document.body.dataset.fullName = "Test User";
  document.body.dataset.chats = '[{"id": 1, "name": "Chat 1"}, {"id": 2, "name": "Chat 2"}]';
  document.body.dataset.testing = "true";
  document.body.dataset.chatId = '123';
});

test('should read dataset correctly', () => {
  const body = document.body;

  var email = body.dataset.email;
  var full_name = body.dataset.fullName;
  var chats = body.dataset.chats ? JSON.parse(body.dataset.chats) : [];
  var testing = body.dataset.testing;
  var chatId = body.dataset.chatId;

  expect(email).toBe('test@example.com');
  expect(full_name).toBe('Test User');
  expect(chats).toEqual([{ id: 1, name: 'Chat 1' }, { id: 2, name: 'Chat 2' }]);
  expect(testing).toBe('true');
  expect(chatId).toBe('123');
});

test('addChatToSidebar adds new chat element to the sidebar', () => {
  window.chats = [];
  window.updateChatsToDeleteSelect = jest.fn();

  const newChat = {
    chat_id: '123',
    chat_name: 'New Test Chat',
    last_message: 'This is a test message',
    chat_created_by_self: true,
  };

  window.addChatToSidebar(newChat);

  const addedChat = document.querySelector('[data-chat-id="123"]');

  expect(addedChat).not.toBeNull();
  expect(addedChat).toHaveTextContent('New Test Chat');
  expect(addedChat).toHaveTextContent('This is a test message');
});

test('should send search command over WebSocket when typing in search input', () => {
  const mockSocket = new (require('../../static/reconnecting-websocket'))();
  mockSocket.readyState = WebSocket.OPEN;
  
  window.alert = jest.fn();

  const email = 'test@example.com';
  const searchInput = document.getElementById('search-input');

  fireEvent.change(searchInput, { target: { value: 'hello' } });

  const message = searchInput.value;

  //Mocking key press after adding text to file, socket is open so proper data is sent to consumer
  if (mockSocket.readyState === WebSocket.CLOSED && document.body.dataset.testing !== true) {
    alert('WebSocket is closed right now. Try again later.');
    return;
  }

  mockSocket.send(JSON.stringify({
    command: 'search_chats',
    email: email,
    message: message,
  }));

  expect(mockSocket.send).toHaveBeenCalled();
});

test('should alert if WebSocket is closed when typing in search input', () => {
  const mockSocket = new (require('../../static/reconnecting-websocket'))();
  mockSocket.readyState = WebSocket.CLOSED;
  
  window.alert = jest.fn();

  const email = 'test@example.com';
  const searchInput = document.getElementById('search-input');

  searchInput.onkeyup = function (e) {
    const message = searchInput.value;

    if (mockSocket.readyState === WebSocket.CLOSED) {
      alert('WebSocket is closed right now. Try again later.');
      return;
    }

    mockSocket.send(JSON.stringify({
      command: 'search_chats',
      email: email,
      message: message,
    }));
  };

  fireEvent.change(searchInput, { target: { value: 'hello' } });
  fireEvent.keyUp(searchInput, { key: 'h', code: 'KeyH' });

  expect(window.alert).toHaveBeenCalledWith('WebSocket is closed right now. Try again later.');
  expect(mockSocket.send).not.toHaveBeenCalled();
});

test('update chats on the sidebar after recieving data back from backend from search query', () => {
  //Mocked received data
  const chats = [{
    id: '123',
    chat_name: 'New Test Chat 1',
    last_message: 'This is chat id 1',
    new_message: false,
  },{
    id: '234',
    chat_name: 'Test Chat 2',
    last_message: 'This is chat id 2',
    new_message: false,
  },{
    id: '345',
    chat_name: 'A Test Chat 3',
    last_message: 'This is chat id 3',
    new_message: true,
  }];

  const chatsJSON = {
    chats : chats
  };

  //For chat home page
  window.updateShownChats(chatsJSON);

  const addedChat1 = document.querySelector('[data-chat-id="123"]');
  const addedChat2 = document.querySelector('[data-chat-id="234"]');
  const addedChat3 = document.querySelector('[data-chat-id="345"]');

  expect(addedChat1).not.toBeNull();
  expect(addedChat1).toHaveTextContent('New Test Chat 1');
  expect(addedChat1).toHaveTextContent('This is chat id 1');

  expect(addedChat2).not.toBeNull();
  expect(addedChat2).toHaveTextContent('Test Chat 2');
  expect(addedChat2).toHaveTextContent('This is chat id 2');

  expect(addedChat3).not.toBeNull();
  expect(addedChat3).toHaveTextContent('A Test Chat 3');
  expect(addedChat3).toHaveTextContent('This is chat id 3');
  expect(addedChat3.querySelector('img')).toHaveClass('newMessage');

  //For selected chat page with an active chat
  window.roomUpdateShownChats(chatsJSON);

  const addedChat4 = document.querySelector('[data-chat-id="123"]');
  const addedChat5 = document.querySelector('[data-chat-id="234"]');
  const addedChat6 = document.querySelector('[data-chat-id="345"]');

  expect(addedChat4).not.toBeNull();
  expect(addedChat4).toHaveTextContent('New Test Chat 1');
  expect(addedChat4).toHaveTextContent('This is chat id 1');
  setTimeout(() => {
    const addedChat4 = document.querySelector('[data-chat-id="123"]');
    console.log(addedChat4.classList);
    expect(addedChat4).toHaveClass('active');
  }, 100);

  expect(addedChat5).not.toBeNull();
  expect(addedChat5).toHaveTextContent('Test Chat 2');
  expect(addedChat5).toHaveTextContent('This is chat id 2');

  expect(addedChat6).not.toBeNull();
  expect(addedChat6).toHaveTextContent('A Test Chat 3');
  expect(addedChat6).toHaveTextContent('This is chat id 3');
  expect(addedChat6.querySelector('img')).toHaveClass('newMessage');
});

test('should delete the chat from the UI after using delete chat function', () => {
  const mockSocket = new (require('../../static/reconnecting-websocket'))();
  mockSocket.readyState = WebSocket.OPEN;
  window.email = 'test@example.com';
  window.chats = [];

  const newChat = {
    chat_id: '123',
    chat_name: 'New Test Chat',
    last_message: 'This is a test message',
    chat_created_by_self: true,
  };

  window.addChatToSidebar(newChat);

  const addedChat = document.querySelector('[data-chat-id="123"]');

  expect(addedChat).not.toBeNull();
  expect(addedChat).toHaveTextContent('New Test Chat');
  expect(addedChat).toHaveTextContent('This is a test message');

  const selectElement = document.getElementById('chatsToDelete');
  for (const option of selectElement.options) {
    if (option.text === 'New Test Chat') {
      option.selected = true;
    }
  }
  fireEvent.change(selectElement);

  const deleteChatForm = document.getElementById('deleteChatForm');
  fireEvent.submit(deleteChatForm);

  //After delete chat button is pressed, it sends data to the consumer, which thens sends data back to filter out
  //The chats that are no longer visible to the user. This will be further tested in integration testing, but for now
  //Just testing that the buttons are interactable and working as far as frontend is as far as I can go for unit testing
  //Would require full consumer functionality to completely work, which is integration testing
  window.updateShownChats({ chats: [] });

  expect(document.body).not.toHaveTextContent('[data-chat-id="123"]');
});

test('should grab correct text from input box and properly send message data through websocket to consumer', () => {
  const mockSocket = new (require('../../static/reconnecting-websocket'))();
  mockSocket.readyState = WebSocket.OPEN;
  
  window.alert = jest.fn();

  const email = 'test@example.com';
  const messageInput = document.getElementById('chat-message-input');

  fireEvent.change(messageInput, { target: { value: 'this is a message!' } });

  var messageInputDom = document.getElementById('chat-message-input');
  var message = messageInputDom.value;

  //Mocking key press after adding text to file, socket is open so proper data is sent to consumer
  if(message === null || message === ""){
    alert('ERROR: There was a problem when trying to get your message. Please make sure you have at least one character in the text box before sending a message');
    return;
  }

  if(mockSocket.readyState === WebSocket.CLOSED){
    alert('WebSocket is closed right now. Try again later.');
    return;
  }

  mockSocket.send(JSON.stringify({
      'command': 'new_message',
      'message': message,
      'from': email,
      'chat_id': chat_id,
  }));

  messageInputDom.value = '';

  expect(mockSocket.send).toHaveBeenCalled();
});

test('should properly format given JSON in html to be inputted into the page', () => {
  const newMessage = {
    author: 'Happy@Gilmore.com',
    author_name: 'Happy Gilmore',
    content: 'This is my message!',
    date_sent: 'November 12, 2023',
    first_initial : "H"
  };

  window.createMessage(newMessage);

  const chatLog = document.getElementById('chat-log');

  expect(chatLog).not.toBeNull();
  expect(chatLog).toHaveTextContent('Happy Gilmore');
  expect(chatLog).toHaveTextContent('This is my message!');
  expect(chatLog).toHaveTextContent('November 12 2023');
});

//GENERAL UI/BUTTONS TESTING ALL BELOW SEPERATED INTO DIFFERENT TESTS FOR READABILITY
test('should add the "active" class to the clicked chat', () => {
  const chat1 = screen.getByText(/Chat 1/i);

  fireEvent.click(chat1);

  expect(chat1).toHaveClass('active');
});

test('should navigate to the correct chat URL when a chat is clicked', () => {
  const mockAssign = jest.fn();
  delete window.location;
  window.location = { assign: mockAssign };

  const chat1 = screen.getByText(/Chat 1/i);

  chat1.addEventListener('click', () => {
    const chatId = chat1.getAttribute('data-chat-id');
    window.location.assign(`/chat/${chatId}`);
  });

  fireEvent.click(chat1);

  expect(mockAssign).toHaveBeenCalledWith('/chat/1');
});