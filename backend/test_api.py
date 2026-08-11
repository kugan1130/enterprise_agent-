import json, requests, time

BASE_URL = 'http://127.0.0.1:8000/api/chat'
SESSION_ID = 'testsession'

def send_query(message):
    payload = {'message': message, 'session_id': SESSION_ID}
    try:
        resp = requests.post(BASE_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print('QUERY:', message)
        print('RESPONSE:', data.get('response'))
        return data.get('response')
    except Exception as e:
        print('Error for', message, e)
        return None

if __name__ == '__main__':
    tests = [
        ('hi', 'direct'),
        ('Kugan is an AI Engineer.', 'ack'),
        ('Is Kugan an AI Engineer?', 'direct'),
        ("What is Kugan's profession?", 'direct'),
        ('How many products did my company sell?', 'sql'),
        ('Who is Kanishka?', 'rag'),
        ('Kugan profession?', 'direct'),
        ('What is our company leave policy?', 'rag'),
        ('Who is the current CM of Tamil Nadu?', 'web'),
        ('Who is the CM of Atlantis?', 'noresult'),
    ]
    for q, expected in tests:
        send_query(q)
        time.sleep(0.2)
