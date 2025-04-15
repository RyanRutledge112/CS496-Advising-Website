import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as roomBase from '../../static/room_base.js';

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

beforeEach(() => {
  document.body.innerHTML = `
    <body>
      <div id="chats">
        <ul>
          <li class="chat" data-chat-id="1" id="chat-1">Chat 1</li>
          <li class="chat" data-chat-id="2" id="chat-2">Chat 2</li>
        </ul>
      </div>
      <input type="text" id="search-input" />
      <select id="chatsToDelete"></select>
    </body>
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
});

test('should read dataset correctly', () => {
  const body = document.body;

  var email = body.dataset.email;
  var full_name = body.dataset.fullName;
  var chats = body.dataset.chats ? JSON.parse(body.dataset.chats) : [];
  var testing = body.dataset.testing;

  expect(email).toBe('test@example.com');
  expect(full_name).toBe('Test User');
  expect(chats).toEqual([{ id: 1, name: 'Chat 1' }, { id: 2, name: 'Chat 2' }]);
  expect(testing).toBe('true');
});

test('addChatToSidebar adds new chat element to the sidebar', () => {
  window.getProfilePicture = () => 'https://example.com/profile.jpg';
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
  expect(addedChat.querySelector('img').src).toContain('https://static-00.iconduck.com/assets.00/n-letter-icon-512x512-52nch8s7.png');
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