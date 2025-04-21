var chats = [];
var email = "";
var full_name = "";
var chatSocket;

window.onload = function () {
  const body = document.body;
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
    full_name = full_name.replace(/^"(.*)"$/, '$1');
  }

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
    removeChatsFromDeleteChatSelect(chatsToDelete)
  })

  if (typeof window !== 'undefined') {
    var wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    chatSocket = new ReconnectingWebSocket(
      wsScheme + '://' + window.location.host + '/ws/chat/home/'
    );
  }

  chatSocket.onopen = function(e) {
    chatSocket.send(JSON.stringify({
      'command': 'load_chats',
      'email': email,
    }));
  }
  
  chatSocket.onmessage = function(e) {
    var data = JSON.parse(e.data);
  
    if (data['command']  === 'new_chat'){
        var newChat = data['chat'];
        addChatToSidebar(newChat);
        if(newChat['chat_created_by_self']){
          setActiveChatById(newChat['id']);
        }
      } else if (data['command'] === 'filter_chats' || data['command'] === 'load_chats'){
        updateShownChats(data);
      } else if (data['command'] === 'chat_ping'){
        showNewMessage(data['chat']);
      }
  }

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

function setActiveChat(clickedChat) {
  document.querySelectorAll('.chat').forEach(chat => {
    chat.classList.remove('active');
  });

  clickedChat.classList.add('active');

  let chat_id = clickedChat.getAttribute('data-chat-id');
  localStorage.setItem("activeChat", chat_id)

  window.location.href = `/chat/${chat_id}`;
}

function updateShownChats(data) {
  var chatList = document.querySelector('#chats ul');
  chatList.innerHTML = "";

  data['chats'].forEach(chat => {
    chat['chat_name'] = chat['chat_name']
      .replace(full_name, "")
      .replace(/^,|,$/g, "")
      .replace(/\s*,\s*/g, ", ")
      .replace(/,\s*,+/g, ',')
      .replace(/^(\s*,\s*)+|(\s*,\s*)+$/g, '')
      .trim();
  });

  data['chats'].sort((a, b) => a['chat_name'].localeCompare(b['chat_name']));

  data['chats'].forEach(chat => {
      var newChatElement = document.createElement('li');
      newChatElement.classList.add('chat');
      newChatElement.setAttribute('data-chat-id', chat['id']);
      newChatElement.setAttribute('onclick', 'setActiveChat(this)');

      var imgClass = chat['new_message'] ? 'newMessage' : '';

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

document.addEventListener("DOMContentLoaded", function() {
  let savedActiveChat = localStorage.getItem("activeChat");
  let currentPath = window.location.pathname;

  if (currentPath === "/chat/") {
      document.querySelectorAll('.chat').forEach(chat => {
        chat.classList.remove("active");
      });
  } else if (savedActiveChat) {
      document.querySelectorAll('.chat').forEach(chat => {
          let chat_id = chat.getAttribute('data-chat-id')

          if (chat_id === savedActiveChat) {
            chat.classList.add("active");
          }
      });
    }
});

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
      console.log(id);
      const option = select.querySelector(`option[value="${id}"]`);
      if (option && option.selected) {
          option.selected = false;
      }
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
      let chat_id = chat.getAttribute('data-chat-id')

      if (String(chat_id) === String(data['chat_id'])) {
        let imgElement = chat.querySelector('img');
        let last_message = chat.querySelector('.preview');

        if(imgElement){
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
  
  return pictures[letter.toLowerCase()] || 'https://www.wku.edu/athletictraditions/images/redtowellogo.gif';
}

window.addChatToSidebar = addChatToSidebar;
window.updateShownChats = updateShownChats;
window.getProfilePicture = getProfilePicture;