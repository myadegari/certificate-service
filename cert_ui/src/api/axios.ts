import axios from 'axios';

const BASE_URL = 'http://127.0.0.1:8000';

const GeneralClient = axios.create({
    baseURL: BASE_URL,
});

const PrivateClient = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export { GeneralClient, PrivateClient };