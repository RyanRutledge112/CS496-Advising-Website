import $ from 'jquery';
global.$ = $;

global.ReconnectingWebSocket = jest.fn().mockImplementation(() => {
    return {
        onmessage: jest.fn(),
        onopen: jest.fn(),
        onclose: jest.fn(),
        send: jest.fn(),
        close: jest.fn()
    };
});

global.WebSocket = require('ws');