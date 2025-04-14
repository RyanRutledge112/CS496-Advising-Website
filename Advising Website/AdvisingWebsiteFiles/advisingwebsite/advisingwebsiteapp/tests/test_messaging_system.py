import random
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from advisingwebsite.asgi import application
from advisingwebsiteapp.models import Chat, ChatMember

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_creation_for_two_members():
    User = get_user_model()

    creator = await sync_to_async(User.objects.create_user)(
        email="creator@example.com",
        password="testpass",
        first_name="ex",
        last_name="ample",
        is_student=True,
        is_advisor=False,
        student_id=102010
    )

    participant = await sync_to_async(User.objects.create_user)(
        email="member@example.com",
        password="testpass",
        first_name="mem",
        last_name="ber",
        is_student=True,
        is_advisor=False,
        student_id=102011
    )

    communicator = WebsocketCommunicator(application, "/ws/chat/home/")
    communicator.scope["user"] = creator
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({
        'command': 'new_chat',
        'chatMemberIDs': [participant.id],
        'chatMemberNames': [f"{participant.get_full_name()}"],
        'createdBy': creator.email
    })

    response = await communicator.receive_json_from()
    assert response['command'] == 'new_chat'
    assert participant.get_full_name() in response['chat']['chat_name']

    chat = await sync_to_async(Chat.objects.get)(chat_name__contains=creator.first_name)
    members = await sync_to_async(lambda: list(chat.members.select_related('user').all()))()

    assert len(members) == 2

    creator_found = False
    participant_found = False
    for m in members:
        if m.user.email == creator.email:
            creator_found = True
        if m.user.email == participant.email:
            participant_found = True

    assert creator_found
    assert participant_found

    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_creation_with_random_participants():
    User = get_user_model()

    creator = await sync_to_async(User.objects.create_user)(
        email="creator@example.com",
        password="testpass",
        first_name="ex",
        last_name="ample",
        is_student=True,
        is_advisor=False,
        student_id=102010
    )

    num_participants = random.randint(3, 30)
    participants = []
    for i in range(num_participants):
        participant = await sync_to_async(User.objects.create_user)(
            email=f"member{i}@example.com",
            password="testpass",
            first_name=f"mem{i}",
            last_name=f"ber{i}",
            is_student=True,
            is_advisor=False,
            student_id=102011 + i
        )
        participants.append(participant)

    communicator = WebsocketCommunicator(application, "/ws/chat/home/")
    communicator.scope["user"] = creator
    connected, _ = await communicator.connect()
    assert connected

    chat_member_ids = [p.id for p in participants]
    chat_member_names = [f"{p.get_full_name()}" for p in participants]

    await communicator.send_json_to({
        'command': 'new_chat',
        'chatMemberIDs': chat_member_ids,
        'chatMemberNames': chat_member_names,
        'createdBy': creator.email
    })

    response = await communicator.receive_json_from()
    assert response['command'] == 'new_chat'

    for p in participants:
        assert p.get_full_name() in response['chat']['chat_name']

    chat = await sync_to_async(Chat.objects.get)(chat_name__contains=creator.first_name)
    members = await sync_to_async(lambda: list(chat.members.select_related('user').all()))()

    assert len(members) == len(participants) + 1

    for p in participants:
        participant_found = any(m.user.email == p.email for m in members)
        assert participant_found

    creator_found = any(m.user.email == creator.email for m in members)
    assert creator_found

    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_loading_for_user_based_on_search():
    User = get_user_model()

    user = await sync_to_async(User.objects.create_user)(
        email="creator@example.com",
        password="testpass",
        first_name="ex",
        last_name="ample",
        is_student=True,
        is_advisor=False,
        student_id=102010
    )

    communicator = WebsocketCommunicator(application, "/ws/chat/home/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected

    participants = []
    for i in range(4):
        participant = await sync_to_async(User.objects.create_user)(
            email=f"member{i}@example.com",
            password="testpass",
            first_name=f"mem{i}",
            last_name=f"ber{i}",
            is_student=True,
            is_advisor=False,
            student_id=102011 + i
        )
        participants.append(participant)

        await communicator.send_json_to({
            'command': f'new_chat',
            'chatMemberIDs': [participant.id],
            'chatMemberNames': [f'{participant.get_full_name()}'],
            'createdBy': user.email
        })

    await communicator.send_json_to({
        'command': 'search_chats',
        'message': 'mem2',
        'email': user.email
    })

    #Filter through uneccesary responses from the consumer for this test
    for i in range(10):
        response = await communicator.receive_json_from()
        if response['command'] == 'filter_chats':
            break
    
    assert response['command'] == 'filter_chats'
    assert response['chats'][0]['chat_name'] == 'mem2 ber2'