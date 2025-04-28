const body = document.body;
var chatSocket;

var chats = [];
var email = "";
var full_name = "";

var chat_id = body.dataset.chatId;

window.onload = function() {
  var testing = body.dataset.testing;

  if(testing === "true") {
    email = body.dataset.email;
    full_name = body.dataset.fullName;
    chats = body.dataset.chats ? JSON.parse(body.dataset.chats) : [];
  } else {
    email = JSON.parse(body.dataset.email);
    full_name = JSON.parse(body.dataset.fullName);
    chats = JSON.parse(body.dataset.chats);
  
    email = email.replace(/^"(.*)"$/, '$1');
    chat_id = chat_id.replace(/^"(.*)"$/, '$1');
    full_name = full_name.replace(/^"(.*)"$/, '$1');
  }

  document.querySelector('#chat-message-input').onkeyup = function(e) {
    if (e.keyCode === 13) {  // enter, return
        document.querySelector('#chat-message-submit').click();
    }
  };

  document.querySelector('#chat-message-submit').onclick = function(e) {
    var messageInputDom = document.getElementById('chat-message-input');
    var message = messageInputDom.value;

    if(message === null || message === ""){
      alert('ERROR: There was a problem when trying to get your message. Please make sure you have at least one character in the text box before sending a message');
      return;
    }

    if(chatSocket.readyState === WebSocket.CLOSED){
      console.log('WebSocket is not currently ready to send data and is closed.');
      alert('WebSocket is closed right now. Try again later.');
      return;
    }

    chatSocket.send(JSON.stringify({
        'command': 'new_message',
        'message': message,
        'from': email,
        'chat_id': chat_id,
    }));

    messageInputDom.value = '';
  };

  document.querySelector('#search-input').onkeyup = function(e) {
    var messageInputDom = document.getElementById('search-input');
    var message = messageInputDom.value;
  
    if(chatSocket.readyState === WebSocket.CLOSED){
      console.log('WebSocket is not currently ready to send data and is closed.');
      alert('WebSocket is closed right now. Try again later.');
      return;
    }
  
    chatSocket.send(JSON.stringify({
        'command': 'search_chats',
        'email': email,
        'message': message,
    }));
  };

  document.querySelector('.close-add-chat').addEventListener('click', closeModal);

  document.getElementById('newChatForm').addEventListener('submit', function (event) {
    event.preventDefault();
    chatMembers = getSelectedMembers();
  
    if(chatSocket.readyState === WebSocket.CLOSED){
      console.log('WebSocket is not currently ready to send data and is closed.');
      alert('WebSocket is closed right now. Try again later.');
      return;
    }
  
    chatSocket.send(JSON.stringify({
      'command': 'new_chat',
      'chatMemberIDs': chatMembers['ids'],
      'chatMemberNames': chatMembers['names'],
      'createdBy': email
    }));
    closeModal('chatPopup');
    removeChatsFromAddChatSelect(chatMembers['ids']);
  });

  document.getElementById('deleteChatForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var chatsToDelete = getChatsToDelete();
  
    if(chatSocket.readyState === WebSocket.CLOSED){
      console.log('WebSocket is not currently ready to send data and is closed.');
      alert('WebSocket is closed right now. Try again later.');
      return;
    }
  
    chatSocket.send(JSON.stringify({
      'command': 'delete_chats',
      'chatIDs': chatsToDelete,
      'deletedBy': email
    }));
    closeModal('delete-chat-popup');
  
    chats = chats.filter(chat => !chatsToDelete.includes(chat.id));
    removeChatsFromDeleteChatSelect(chatsToDelete);
  
    chatsToDelete.forEach(id => {
      console.log('id: ', id);
      console.log('room id: ', chat_id);
      if (id === chat_id) {
        window.location.href = "/chat/";
      }
    });
  })

  if (typeof window !== 'undefined') {
    var wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    chatSocket = new ReconnectingWebSocket(
      wsScheme + '://' + window.location.host +
      '/ws/chat/' + chat_id + '/'
    );
  }
  
  chatSocket.onopen = function(e) {
    chatSocket.send(JSON.stringify({
      'command': 'load_chats',
      'email': email,
    }));
    fetchMessages();
  };
  
  chatSocket.onmessage = function(e) {
      var data = JSON.parse(e.data);
      if (data['command'] === 'messages') {
        for (let i=0; i<data['messages'].length; i++) {
          createMessage(data['messages'][i]);
        }
      } else if (data['command'] === 'new_message'){
        createMessage(data['message']);
      } else if (data['command']  === 'new_chat'){
        var newChat = data['chat'];
        addChatToSidebar(newChat);
        if(newChat['chat_created_by_self']){
          setActiveChatById(newChat['id']);
        }
      } else if (data['command'] === 'filter_chats'){
        roomUpdateShownChats(data);
      } else if (data['command'] === 'chat_ping'){
        showNewMessage(data['chat']);
      } else if (data['command'] === 'load_chats'){
        loadChats(data);
      } else if (data['command'] === 'error'){
        alert(data['error']);
      }
  };
  
  chatSocket.onclose = function(e) {
      console.error('Chat socket closed unexpectedly');
  };
}

$(document).ready(function() {
  $('#delete-chat').on('click', function () {
    $('#delete-chat-popup').show();
    $('#chatsToDelete').select2({
      placeholder: "Select chats to delete",
      allowClear: true,
    });
  });

  $('#addchat').on('click', function () {
    $('#chatPopup').show();
    $('#chatParticipants').select2({
      placeholder: "Select users",
      allowClear: true,
    });
  });
});

function fetchMessages(retryCount = 0) {
  const MAX_RETRIES = 5;
  const RETRY_DELAY = 500;

  if (chatSocket.readyState === WebSocket.CLOSED) {
    console.log('WebSocket is not currently ready to send data and is closed.');
    alert('WebSocket is closed right now. Try again later.');
    return;
  }

  if (chat_id) {
    chatSocket.send(JSON.stringify({
      'command': 'fetch_messages',
      'chat_id': chat_id
    }));
  } else if (retryCount < MAX_RETRIES) {
    // Wait and retry
    setTimeout(() => {
      fetchMessages(retryCount + 1);
    }, RETRY_DELAY);
  } else {
    console.warn('chat_id not available after multiple retries.');
  }
}

function formatTimeAgo(date) {
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);

  const units = [
    { name: "year", seconds: 31536000 },
    { name: "month", seconds: 2592000 },
    { name: "day", seconds: 86400 },
    { name: "hour", seconds: 3600 },
    { name: "minute", seconds: 60 },
  ];

  for (let unit of units) {
    const interval = Math.floor(diff / unit.seconds);
    if (interval >= 1) {
      return `${interval} ${unit.name}${interval !== 1 ? "s" : ""} ago`;
    }
  }

  return "Just now";
}

function formatFullDate(date) {
  return date.toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZoneName: 'short'
  }).replace(',', '')
    .replace(' at', '');
}

function createMessage(data) {
  var author = data['author'];
  var timestamp = new Date(data['date_sent']);

  var timeText = formatTimeAgo(timestamp);
  var fullDate = formatFullDate(timestamp);

  var msgListTag = document.createElement('li');
  var imgTag = document.createElement('img');
  var messageContainer = document.createElement('div');
  var messageText = document.createElement('p');
  
  if (author === email) {
    msgListTag.className = 'sent';
    imgTag.src = getProfilePicture(full_name[0]);
    messageText.innerHTML += "<strong>" + full_name + "</strong> <br>";
  } else {
    msgListTag.className = 'replies';
    imgTag.src = getProfilePicture(data['first_initial']);
    messageText.innerHTML += "<strong>" + data['author_name'] + "</strong> <br>";
  }

  messageText.innerHTML += data.content + '<br> <small>' + timeText + "<br>" + fullDate + "</small>";

  messageContainer.appendChild(messageText);
  msgListTag.appendChild(imgTag);
  msgListTag.appendChild(messageContainer);
  document.querySelector('#chat-log').appendChild(msgListTag);

  var messagesContainer = document.querySelector('.messages');
  if (messagesContainer) {
    // Scroll to the bottom of the chat
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } else {
    console.warn('Messages container not found');
  }
};

function roomUpdateShownChats(data) {
  const chatList = document.querySelector('#chats ul');
  chatList.innerHTML = "";

  const activeChatId = localStorage.getItem("activeChat");

  data['chats'].forEach(chat => {
    chat['chat_name'] = chat['chat_name']
      .replace(full_name, "")
      .replace(/^,|,$/g, "")
      .replace(/\s*,\s*/g, ", ")
      .replace(/,\s*,+/g, ',')
      .replace(/^(\s*,\s*)+|(\s*,\s*)+$/g, '')
      .trim();
  });

  data['chats'].sort((a, b) => {
    if (String(a.id) === activeChatId) return -1;
    if (String(b.id) === activeChatId) return 1;
    return a.chat_name.localeCompare(b.chat_name);
  });

  data['chats'].forEach(chat => {
    const newChatElement = document.createElement('li');

    newChatElement.classList.add('chat');
    newChatElement.classList.toggle('active', String(chat['id']) === activeChatId);
    newChatElement.setAttribute('data-chat-id', chat['id']);
    newChatElement.setAttribute('onclick', 'setActiveChat(this)');

    const imgClass = chat['new_message'] ? 'newMessage' : '';

    newChatElement.innerHTML = `
      <div class="wrap">
        <img src="${getProfilePicture(chat['chat_name'].charAt(0).toLowerCase())}" class="${imgClass}" alt="${chat['chat_name']}" />
        <div class="meta">
          <p class="name">${chat['chat_name']}</p>
          <p class="preview">${chat['last_message'] || 'No messages yet'}</p>
        </div>
      </div>
    `;

    chatList.appendChild(newChatElement);
  });
}

function loadChats(data) {
  const chatList = document.querySelector('#chats ul');
  chatList.innerHTML = "";

  const activeChatId = localStorage.getItem("activeChat");

  data['chats'].forEach(chat => {
    chat['chat_name'] = chat['chat_name']
      .replace(full_name, "")
      .replace(/^,|,$/g, "")
      .replace(/\s*,\s*/g, ", ")
      .replace(/,\s*,+/g, ',')
      .replace(/^(\s*,\s*)+|(\s*,\s*)+$/g, '')
      .trim();
  });

  data['chats'].sort((a, b) => {
    if (String(a.id) === activeChatId) return -1;
    if (String(b.id) === activeChatId) return 1;
    return a.chat_name.localeCompare(b.chat_name);
  });

  data['chats'].forEach(chat => {
    const newChatElement = document.createElement('li');

    newChatElement.classList.add('chat');
    newChatElement.classList.toggle('active', String(chat['id']) === activeChatId);
    newChatElement.setAttribute('data-chat-id', chat['id']);
    newChatElement.setAttribute('onclick', 'setActiveChat(this)');

    const imgClass = chat['new_message'] ? 'newMessage' : '';

    newChatElement.innerHTML = `
      <div class="wrap">
        <img src="${getProfilePicture(chat['chat_name'].charAt(0).toLowerCase())}" class="${imgClass}" alt="${chat['chat_name']}" />
        <div class="meta">
          <p class="name">${chat['chat_name']}</p>
          <p class="preview">${chat['last_message'] || 'No messages yet'}</p>
        </div>
      </div>
    `;

    chatList.appendChild(newChatElement);
  });

  let savedActiveChat= localStorage.getItem("activeChat");

  if (savedActiveChat) {
    document.querySelectorAll('.chat').forEach(chat => {
        let chat_id = chat.getAttribute('data-chat-id');
        if (String(chat_id) === String(savedActiveChat)) {
          chat.classList.add("active");
        }
    });

    let activeChatElement = document.querySelector(`.chat[data-chat-id="${chat_id}"]`);
    if(activeChatElement){
      let chatName = activeChatElement.querySelector(".name").textContent;
      document.getElementById("chat-name-display").textContent = chatName;
      document.getElementById("chat-image-display").src = getProfilePicture(chatName.charAt(0).toLowerCase())
    }
  }
}

function setActiveChat(clickedChat) {
    let chat_id = clickedChat.getAttribute('data-chat-id');

    fetch(`/chat/check-membership/${chat_id}/`)
    .then(response => response.json())
    .then(data => {
      if(data.is_member) {
        let currentActiveChat = localStorage.getItem("activeChat");

        if (String(chat_id) === String(currentActiveChat)) {
            localStorage.removeItem("activeChat");
            window.location.href = "/chat/";
        } else {
            document.querySelectorAll('.chat').forEach(chat => {
                chat.classList.remove('active');
            });

            clickedChat.classList.add('active');
            localStorage.setItem("activeChat", chat_id);
            window.location.href = `/chat/${chat_id}`;
        }
      } else {
        alert("You are not authorized to access this chat.");
      }
    })
    .catch(error => console.error("Error checking chat membership: ", error));
}

document.addEventListener("DOMContentLoaded", function () {
  var addChatBtn = document.getElementById("addchat");
  var chatPopup = document.getElementById("chatPopup");
  var closeAddChatBtn = document.querySelector(".close-add-chat");

  var deleteChatBtn = document.getElementById("delete-chat");
  var deleteChatPopup = document.getElementById("delete-chat-popup");
  var closeDeleteChatBtn = document.querySelector(".close-delete-chat");

  if (addChatBtn && chatPopup && closeAddChatBtn) {
    addChatBtn.addEventListener("click", function () {
      openModal('chatPopup');
    });

    closeAddChatBtn.addEventListener("click", function () {
      closeModal('chatPopup');
    });

    window.addEventListener("click", function (event) {
      if (chatPopup && event.target === chatPopup) {
        closeModal('chatPopup');
      }
    });
  }

  if (deleteChatBtn && deleteChatPopup && closeDeleteChatBtn) {
    deleteChatBtn.addEventListener("click", function () {
      openModal('delete-chat-popup');
    });

    closeDeleteChatBtn.addEventListener("click", function () {
      closeModal('delete-chat-popup');
    });

    window.addEventListener("click", function (event) {
      if (deleteChatPopup && event.target === deleteChatPopup) {
        closeModal('delete-chat-popup');
      }
    });
  }
});

function openModal(popup) {
  document.getElementById(popup).style.display = 'block';
  document.documentElement.classList.add('modal-open');
  document.body.classList.add('modal-open');
}

function closeModal(popup) {
  const modal = document.getElementById(popup);
  if (!modal) return;
  modal.style.display = 'none';
  document.documentElement.classList.remove('modal-open');
  document.body.classList.remove('modal-open');
}

function getSelectedMembers() {
  var selectedMembers = $('#chatParticipants').val();
  var selectedNames = $('#chatParticipants option:selected').map(function() {
    return $(this).text();
  }).get();

  return { 'ids': selectedMembers, 'names': selectedNames };
}

function getChatsToDelete(){
  var selectedChats = $('#chatsToDelete').val();
  var selectedChatNames = $('#chatsToDelete option:selected').map(function() {
    return $(this).text();
  }).get();

  console.log("Selected Chat IDs: ", selectedChats);
  console.log("Selected Chat Names:", selectedChatNames);

  return selectedChats;
}

function removeChatsFromDeleteChatSelect(chatIds) {
  const select = document.getElementById('chatsToDelete');
  chatIds.forEach(id => {
      const option = select.querySelector(`option[value="${id}"]`);
      if (option) option.remove();
  });
}

function removeChatsFromAddChatSelect(chatIds) {
  const select = document.getElementById('chatParticipants');
  chatIds.forEach(id => {
      const option = select.querySelector(`option[value="${id}"]`);
      if (option) option.remove();
  });
}

function addChatToSidebar(newChat) {
    var chatList = document.querySelector('#chats ul');

    var existingChat = chatList.querySelector(`[data-chat-id="${newChat['chat_id']}"]`);
    if (existingChat) {
        return;
    }
    
    var newChatElement = document.createElement('li');
    newChatElement.classList.add('chat');
    newChatElement.setAttribute('data-chat-id', newChat['chat_id']);
    newChatElement.setAttribute('onclick', 'setActiveChat(this)');
    
    newChatElement.innerHTML = `
        <div class="wrap">
            <img src="${getProfilePicture(newChat['chat_name'].charAt(0).toLowerCase())}" alt="${newChat['chat_name']}" />
            <div class="meta">
                <p class="name">${newChat['chat_name']}</p>
                <p class="preview">${newChat['last_message']}</p>
            </div>
        </div>
    `;

    chatList.appendChild(newChatElement);
    if(newChat['chat_created_by_self']){
      newChatElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    var newChatObject = {
      "name": newChat['chat_name'],
      "image_url": getProfilePicture(newChat['chat_name'].charAt(0).toLowerCase()),
      "members": [],
      "chat_id": newChat['chat_id'],
      "last_message": "No messages yet." 
    }

    chats.push(newChatObject)
    updateChatsToDeleteSelect();
}

function updateChatsToDeleteSelect() {
  const select = document.getElementById('chatsToDelete');
  select.innerHTML = '';

  chats.forEach(chat => {
      const option = document.createElement('option');
      option.value = chat.chat_id;
      option.textContent = chat.name;
      select.appendChild(option);
  });
}

function setActiveChatById(chat_id) {
    var chatElement = document.querySelector(`[data-chat-id="${chat_id}"]`);
    if (chatElement) {
        setActiveChat(chatElement);
    }
}

function showNewMessage(data) {
  document.querySelectorAll('.chat').forEach(chat => {
      let id = chat.getAttribute('data-chat-id')

      if(String(id) !== String(chat_id)){
        chatSocket.send(JSON.stringify({
          'command': 'update_last_viewed',
          'chat_id': chat_id,
          'email': email
        }));
      }

      if (String(id) === String(data['chat_id'])) {
        let imgElement = chat.querySelector('img');
        let last_message = chat.querySelector('.preview');

        if(imgElement && String(id) !== String(chat_id)){
          imgElement.classList.add('newMessage');
        }
        if(last_message){
          last_message.textContent = data['last_message'];
        }
      }
  });
}

function getProfilePicture(letter) {
  //Stored generic profile pictures
  const pictures = {
      "a": "https://static-00.iconduck.com/assets.00/a-letter-icon-512x512-j1mhihj0.png",
      "b": "https://static-00.iconduck.com/assets.00/b-letter-icon-512x512-90rzacib.png",
      "c": "https://static-00.iconduck.com/assets.00/c-letter-icon-512x512-6mbkqdec.png",
      "d": "https://static-00.iconduck.com/assets.00/d-letter-icon-512x512-r9lvazse.png",
      "e": "https://static-00.iconduck.com/assets.00/e-letter-icon-512x512-dt9oea54.png",
      "f": "https://static-00.iconduck.com/assets.00/f-letter-icon-512x512-xg6ht0dr.png",
      "g": "https://static-00.iconduck.com/assets.00/g-letter-icon-512x512-6pmz2jsc.png",
      "h": "https://static-00.iconduck.com/assets.00/h-letter-icon-512x512-x6qbinvo.png",
      "i": "https://static-00.iconduck.com/assets.00/i-letter-icon-512x512-dmvytbti.png",
      "j": "https://static-00.iconduck.com/assets.00/j-letter-icon-512x512-x0xc0g9u.png",
      "k": "https://static-00.iconduck.com/assets.00/k-letter-icon-512x512-7bxyhgb3.png",
      "l": "https://static-00.iconduck.com/assets.00/l-letter-icon-512x512-y3zwxhv2.png",
      "m": "https://static-00.iconduck.com/assets.00/m-letter-icon-512x512-dfiryt7g.png",
      "n": "https://static-00.iconduck.com/assets.00/n-letter-icon-512x512-52nch8s7.png",
      "o": "https://static-00.iconduck.com/assets.00/o-letter-icon-512x512-sj7vxh47.png",
      "p": "https://static-00.iconduck.com/assets.00/p-letter-icon-512x512-h5sw1to6.png",
      "q": "https://static-00.iconduck.com/assets.00/q-letter-icon-512x512-30ov2ad6.png",
      "r": "https://static-00.iconduck.com/assets.00/r-letter-icon-512x512-l2j45l27.png",
      "s": "https://static-00.iconduck.com/assets.00/s-letter-icon-512x512-a5ximws6.png",
      "t": "https://static-00.iconduck.com/assets.00/t-letter-icon-512x512-bg5zozzy.png",
      "u": "https://static-00.iconduck.com/assets.00/u-letter-icon-512x512-131g3vfy.png",
      "v": "https://static-00.iconduck.com/assets.00/v-letter-icon-512x512-hjcawsh7.png",
      "w": "https://static-00.iconduck.com/assets.00/w-letter-icon-512x512-1nemv88f.png",
      "x": "https://static-00.iconduck.com/assets.00/x-letter-icon-512x512-3xx065ts.png",
      "y": "https://static-00.iconduck.com/assets.00/y-letter-icon-512x512-ob5jvz98.png",
      "z": "https://static-00.iconduck.com/assets.00/z-letter-icon-512x512-puk3v0kb.png"
  };
  
  return pictures[letter.toLowerCase()];
}

window.roomUpdateShownChats = roomUpdateShownChats;
window.createMessage = createMessage;