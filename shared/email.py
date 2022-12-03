from django.conf import settings
from django.template.loader import render_to_string

import os
import logging

from smtplib import SMTPException
from trench.backends.base import AbstractMessageDispatcher
from trench.responses import DispatchResponse, FailedDispatchResponse, SuccessfulDispatchResponse

from .services import send_mailgun_email


class SendMailMessageDispatcher(AbstractMessageDispatcher):
    def dispatch_message(self) -> DispatchResponse:
        context = {'code': self.create_code()}

        try:
            email_subject = 'Your one-time verification code is ' + context.get('code')
            email_body = render_to_string(
                os.path.join(settings.BASE_DIR, 'templates', 'emails', 'two_factor_code.jinja2'),
                context
            )

            send_mailgun_email(self._to, email_subject, email_body, 'auth')

            return SuccessfulDispatchResponse(details='Email message with MFA code has been sent.')

        except SMTPException as cause:
            logging.error(cause, exc_info=True)
            return FailedDispatchResponse(details=str(cause))

        except ConnectionRefusedError as cause:
            logging.error(cause, exc_info=True)
            return FailedDispatchResponse(details=str(cause))
