from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json

from advisingwebsiteapp.models import Message, Chat, ChatMember
from django.db.models import OuterRef, Subquery, Case, When, Value, F, TextField, DateTimeField, BooleanField
from django.db.models.functions import Coalesce
from django.utils import timezone

User = get_user_model()

class ChatConsumer(WebsocketConsumer):

    def fetch_messages(self, data):
        chat = Chat.objects.filter(id=data['chat_id']).first()
        messages = chat.last_30_messages()
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
        chat = Chat.objects.filter(id=data['chat_id']).first()

        message = Message.objects.create(
            sent_by_member=chat_member,
            chat=chat,
            message_content=data['message'])
        
        participants = ChatMember.objects.filter(chat=chat).select_related('user')

        #sends message out to participants in the chat so their chats are dynamically updated as necessary
        for member in participants:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{member.user.id}',
                {
                    'type': 'chat_message',
                    'message': {
                        'command': 'chat_ping',
                        'chat': {
                            'chat_id': chat.id,
                            'last_message': data['message'],
                            'message_created_by_self': False
                        }
                    }
                }
            )

        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
        }
        return self.send_chat_message(content)

    def new_chat(self, data):
        chat_maker = User.objects.filter(email=data['createdBy']).first()
        selected_member_ids = set(map(int, data['chatMemberIDs']))
        selected_member_ids.add(chat_maker.id)
        print(f"Member ids: {selected_member_ids}")

        user_chats = ChatMember.objects.filter(user=chat_maker).values_list('chat_id', flat=True)

        for chat_id in user_chats:
            participants = ChatMember.objects.filter(chat_id=chat_id).values_list('user_id', flat=True)
            participant_ids = set(participants)
            print(f"Member ids: {participant_ids}")

            print(participant_ids == selected_member_ids)

            if participant_ids == selected_member_ids:
                return self.send_message({
                    'command': 'error',
                    'error': 'A chat with these members already exists.'
                })

        chat_name = f"{chat_maker.get_full_name()}"
        for chatMemberName in data['chatMemberNames']:
            chat_name += f', {chatMemberName}'
            
        new_chat = Chat.objects.create(chat_name=chat_name)

        ChatMember.objects.create(user=chat_maker, chat=new_chat)

        for chatMemberID in data['chatMemberIDs']:
            ChatMember.objects.create(
                user=User.objects.filter(id=chatMemberID).first(),
                chat=new_chat
            )
            
        participants = ChatMember.objects.filter(chat=new_chat).select_related('user')

        #Sends new chat info to participants to dynamically update chat page
        for member in participants:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{member.user.id}',
                {
                    'type': 'chat_message',
                    'message': {
                        'command': 'new_chat',
                        'chat': {
                            'chat_id': new_chat.id,
                            'chat_name': new_chat.chat_name.replace(member.user.get_full_name(), "").strip(', ').replace(" ,", ""),
                            'last_message': 'No messages yet.',
                            'chat_created_by_self': False
                        }
                    }
                }
            )
        
        return self.send_message({
            'command': 'new_chat',
            'chat': {
                'chat_id': new_chat.id,
                'chat_name': new_chat.chat_name.replace(chat_maker.get_full_name(), "").strip(', ').replace(" ,", ""),
                'last_message': 'No messages yet.',
                'chat_created_by_self': True
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
            'author_name': message.sent_by_member.user.get_full_name(),
            'content': message.message_content,
            'date_sent': str(message.date_sent),
            'first_initial': message.sent_by_member.user.get_short_name()[0].lower()
        }
    
    def search_chats(self, data):
        user = User.objects.filter(email=data['email']).first()

        last_message_content_subquery = Message.objects.filter(
            chat=OuterRef('chat_id')
        ).order_by('-date_sent').values('message_content')[:1]

        last_message_date_subquery = Message.objects.filter(
            chat=OuterRef('chat_id')
        ).order_by('-date_sent').values('date_sent')[:1]

        chat_memberships = ChatMember.objects.filter(
            user=user,
            chat_deleted=False
        ).annotate(
            last_message=Coalesce(
                Subquery(last_message_content_subquery, output_field=TextField()),
                Value("", output_field=TextField())
            ),
            last_message_date=Subquery(last_message_date_subquery, output_field=DateTimeField()),
            new_message=Case(
                When(
                    last_message_date__gt=F('chat_last_viewed'),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        ).select_related("chat")

        filtered_chats = [{
            "id": cm.chat.id,
            "chat_name": cm.chat.chat_name.replace(user.get_full_name(), "").strip(", ").replace(" ,", ""),
            "last_message": cm.last_message,
            "new_message": cm.new_message
        } for cm in chat_memberships if data['message'].lower() in cm.chat.chat_name.lower()]

        return self.send_message({
            'command': 'filter_chats',
            'chats': list(filtered_chats)
        })
    
    def load_chats(self, data):
        user = User.objects.filter(email=data['email']).first()

        last_message_content_subquery = Message.objects.filter(
            chat=OuterRef('chat_id')
        ).order_by('-date_sent').values('message_content')[:1]

        last_message_date_subquery = Message.objects.filter(
            chat=OuterRef('chat_id')
        ).order_by('-date_sent').values('date_sent')[:1]

        chat_memberships = ChatMember.objects.filter(
            user=user,
            chat_deleted=False
        ).annotate(
            last_message=Coalesce(
                Subquery(last_message_content_subquery, output_field=TextField()),
                Value("", output_field=TextField())
            ),
            last_message_date=Subquery(last_message_date_subquery, output_field=DateTimeField()),
            new_message=Case(
                When(
                    last_message_date__gt=F('chat_last_viewed'),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        ).select_related("chat")

        filtered_chats = [{
            "id": cm.chat.id,
            "chat_name": cm.chat.chat_name.replace(user.get_full_name(), "").strip(", ").replace(" ,", ""),
            "last_message": cm.last_message,
            "new_message": cm.new_message
        } for cm in chat_memberships ]

        return self.send_message({
            'command': 'load_chats',
            'chats': list(filtered_chats)
        })
    
    def delete_chats(self, data):
        user = User.objects.filter(email=data['deletedBy']).first()

        for chat_id in data['chatIDs']:
            chat_member = ChatMember.objects.filter(user=user, chat_id=chat_id).first()
            if chat_member:
                chat_member.chat_deleted = True
                chat_member.save()

            all_members = ChatMember.objects.filter(chat_id=chat_id)
            if all(member.chat_deleted for member in all_members):
                Chat.objects.filter(id=chat_id).delete()

        self.search_chats({
            'email': data['deletedBy'],
            'message': ''
        })

    def update_last_viewed(self, data):
        user = User.objects.filter(email=data['email']).first()
        chat = Chat.objects.filter(id=data['chat_id']).first()
        user_member = ChatMember.objects.filter(user=user, chat=chat).first()

        if(user_member):
            user_member.chat_last_viewed = timezone.now()
            user_member.save()

    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message,
        'new_chat': new_chat,
        'search_chats': search_chats,
        'delete_chats': delete_chats,
        'update_last_viewed': update_last_viewed,
        'load_chats': load_chats
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

        #Main chat group for communication between chat members
        async_to_sync(self.channel_layer.group_add)(
            self.room_id,
            self.channel_name
        )
        #Personal group to allow users to receive chats as they're being created
        async_to_sync(self.channel_layer.group_add)(
            f'user_{self.user.id}',
            self.channel_name
        )
        self.accept()
    
    async def is_member(self, user, chat_id):
        chat = Chat.objects.filter(id=chat_id).first()
        return ChatMember.objects.filter(chat=chat, user=user).aexists()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_id,
            self.channel_name
        )
        async_to_sync(self.channel_layer.group_discard)(
        f"user_{self.user.id}",
        self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)

        if not self.chat_id == "home":
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