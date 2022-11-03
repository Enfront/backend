import requests
import os


class RecaptchaValidation:
    def __init__(self, token=None):
        data = {
            'secret': os.environ['RECAPTCHA_PRIVATE_KEY'],
            'response': token,
        }

        self.test_token(data)

    def test_token(self, data):
        request = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = request.json()

        if result['success'] and result['score'] >= 0.5:
            return True

        return False
