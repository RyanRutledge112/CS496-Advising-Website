import { addChatToSidebar, updateShownChats, setActiveChatById, setActiveChat } from './chatFunctions';

// Mocking necessary DOM elements
document.body.innerHTML = `
  <div id="chats">
    <ul></ul>
  </div>
`;

describe('Chat creation functions', () => {

  test('addChatToSidebar adds new chat to the sidebar', () => {
    const newChat = {
      id: 1,
      chat_name: "Chat 1",
      chat_created_by_self: true,
    };

    addChatToSidebar(newChat);

    const chatList = document.querySelector('#chats ul');
    const chatElement = chatList.querySelector('li');
    
    expect(chatList.children.length).toBe(1);
    expect(chatElement).toHaveTextContent('Chat 1');
  });

  test('updateShownChats updates the chat list correctly', () => {
    const data = {
      chats: [
        { id: 1, chat_name: "Chat 1", last_message: 'Hello', new_message: true },
        { id: 2, chat_name: "Chat 2", last_message: 'Hi', new_message: false },
      ]
    };

    updateShownChats(data);

    const chatList = document.querySelector('#chats ul');
    const chatItems = chatList.querySelectorAll('li');

    expect(chatItems.length).toBe(2);
    expect(chatItems[0].querySelector('.name').textContent).toBe('Chat 1');
    expect(chatItems[1].querySelector('.name').textContent).toBe('Chat 2');
  });

  test('setActiveChatById sets the active chat', () => {
    const chatList = document.querySelector('#chats ul');
    const chatElement = document.createElement('li');
    chatElement.setAttribute('data-chat-id', 1);
    chatList.appendChild(chatElement);

    setActiveChatById(1);
    
    expect(chatElement.classList.contains('active')).toBe(true);
  });

  test('setActiveChat sets the correct active chat and redirects', () => {
    const chatList = document.querySelector('#chats ul');
    const chatElement = document.createElement('li');
    chatElement.setAttribute('data-chat-id', 1);
    chatList.appendChild(chatElement);
    
    const spy = jest.spyOn(window.location, 'href', 'set');
    
    setActiveChat(chatElement);

    expect(chatElement.classList.contains('active')).toBe(true);
    expect(spy).toHaveBeenCalledWith("/chat/1");
  });

});