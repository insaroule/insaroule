from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from accounts.tests.factories import UserFactory


class TestEmailVerify(TestCase):
    """Test cases for email verification system."""

    def test_last_email_verification_sent(self):
        """Test that last_verification_email_sent is updated when an email is sent."""
        user = UserFactory(email_verified=False, last_verification_email_sent=None)
        self.client.force_login(user)
        self.client.post(reverse("accounts:verify_email_send_token"))
        user.refresh_from_db()
        self.assertIsNotNone(user.last_verification_email_sent)

    @patch("accounts.tasks.send_verification_email.delay")
    def test_send_verification_email(self, mock_send):
        """Test that the user can send email only if it has no cooldown."""
        user = UserFactory(email_verified=False)
        self.client.force_login(user)

        user.last_verification_email_sent = timezone.now()
        self.client.post(reverse("accounts:verify_email_send_token"))
        self.assertTrue(mock_send.called)

        # Simulate a user with a cooldown period
        user.last_verification_email_sent = timezone.now()
        self.client.post(reverse("accounts:verify_email_send_token"))
        self.assertEqual(
            mock_send.call_count, 1
        )  # Should not call again if cooldown is active


class TestLoginPreferredLanguage(TestCase):
    """Test cases for login preferred language setting."""

    def test_login_sets_language_cookie(self):
        """Ensure login response sets the preferred language cookie."""
        user = UserFactory(preferred_language="fr", email_verified=True)
        user.raw_password = "testpassword"
        user.set_password(user.raw_password)
        user.save()
        # Before login, no language cookie
        r = self.client.get(reverse("carpool:list"))
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, r.cookies)

        # Login
        r = self.client.post(
            reverse("accounts:login"),
            {"username": user.username, "password": user.raw_password},
        )

        # After login, language cookie should be set to 'fr'
        self.assertIn(settings.LANGUAGE_COOKIE_NAME, r.cookies)
        self.assertEqual(r.cookies[settings.LANGUAGE_COOKIE_NAME].value, "fr")

    def test_set_language(self):
        """Test that setting the language updates the session."""
        # The only language for now are 'en' and 'fr'
        user = UserFactory(preferred_language="fr", email_verified=True)
        self.assertEqual(user.preferred_language, "fr")
        self.client.force_login(user)

        # Change to en
        self.client.post(reverse("set_user_language"), {"language": "en"})
        user.refresh_from_db()
        self.assertEqual(user.preferred_language, "en")

        # Change back to fr
        self.client.post(reverse("set_user_language"), {"language": "fr"})
        user.refresh_from_db()
        self.assertEqual(user.preferred_language, "fr")

        # Change to an invalid language (no change)
        self.client.post(reverse("set_user_language"), {"language": "xx"})
        user.refresh_from_db()
        self.assertEqual(user.preferred_language, "fr")
