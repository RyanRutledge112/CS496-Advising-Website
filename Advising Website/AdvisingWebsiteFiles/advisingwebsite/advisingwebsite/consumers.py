from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json
from advisingwebsiteapp.models import Message, Chat, ChatMember

User = get_user_model()

class ChatConsumer(WebsocketConsumer):

    def fetch_messages(self, data):
        chat = Chat.objects.filter(id=data['chat_id']).first()
        messages = chat.last_10_messages()
        messages = messages[::-1] #Flips message order so they are in the correct order to be displayed
        content = {
            'command': 'messages',
            'messages': self.messages_to_json(messages)
        }
        self.send_message(content)

    def new_message(self, data):
        author = data['from']
        user = User.objects.filter(email=author).first()
        chat_member = user.joined_chats.filter(chat__id=data['chat_id']).first()
        message = Message.objects.create(
            sent_by_member=chat_member,
            chat=Chat.objects.filter(id=data['chat_id']).first(),
            message_content=data['message'])
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
        }
        return self.send_chat_message(content)

    def new_chat(self, data):
        chat_maker = User.objects.filter(email=data['createdBy']).first()
        chat_name = f"{chat_maker.get_full_name()}"

        for chatMemberName in data['chatMemberNames']:
            chat_name += f', {chatMemberName}'
        
        new_chat = Chat.objects.create(chat_name = chat_name)

        ChatMember.objects.create(
            user = chat_maker,
            chat = new_chat
        )

        for chatMemberID in data['chatMemberIDs']:
            ChatMember.objects.create(
                user = User.objects.filter(id=chatMemberID).first(),
                chat = new_chat
            )
        
        return self.send_message({
            'command': 'new_chat',
            'chat': {
                'chat_id': new_chat.id,
                'chat_name': new_chat.chat_name,
                'image_url': 'http://emilcarlsson.se/assets/louislitt.png',
                'last_message': ''
            }
        })

    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))
        return result

    def message_to_json(self, message):
        return {
            'author': message.sent_by_member.user.email.strip('"'),
            'content': message.message_content,
            'date_sent': str(message.date_sent)
        }

    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message,
        'new_chat': new_chat
    }

    def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_id = 'chat_%s' % self.chat_id
        self.user = self.scope['user']

        if self.user.is_anonymous:
            self.close()
            return

        if not self.chat_id == 'home':
            if not self.is_member(self.user, self.chat_id):
                self.close()
                return

        async_to_sync(self.channel_layer.group_add)(
            self.room_id,
            self.channel_name
        )
        self.accept()
    
    def is_member(self, user, chat_id):
        chat = Chat.objects.filter(id=chat_id).first()
        return ChatMember.objects.filter(chat=chat, user=user).aexists()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_id,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)

        if not self.is_member(self.scope["user"], self.chat_id):
            self.send(text_data=json.dumps({'error': 'Unauthorized'}))

        self.commands[data['command']](self, data)
        

    def send_chat_message(self, message):    
        async_to_sync(self.channel_layer.group_send)(
            self.room_id,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    def send_message(self, message):
        self.send(text_data=json.dumps(message))

    def chat_message(self, event):
        message = event['message']
        self.send(text_data=json.dumps(message))