from django.utils import timezone
from datetime import timedelta
from django.test import TestCase

from accounts.tests.factories import UserFactory
from django.contrib.auth import get_user_model

from accounts import tasks


class DeletingNonVerifiedAccountsTest(TestCase):
    def test_delete_non_verified_account_more_two_weeks(self):
        """Test that the user is deleted if they have not been verified for more than two weeks."""
        date_joined = timezone.now() - timedelta(weeks=3)
        user = UserFactory(
            username="testuser", email_verified=False, date_joined=date_joined
        )
        tasks.delete_non_verified_accounts()
        user = get_user_model().objects.filter(username="testuser")
        self.assertFalse(user.exists())

    def test_delete_non_verified_account_less_two_weeks(self):
        """Test that the user still exist if they have not been verified for less than two weeks."""
        date_joined = timezone.now() - timedelta(weeks=1)
        user = UserFactory(
            username="testuser", email_verified=False, date_joined=date_joined
        )
        tasks.delete_non_verified_accounts()
        user = get_user_model().objects.filter(username="testuser")
        self.assertTrue(user.exists())

    def test_delete_verified_account(self):
        """Test that the user still exist if they have been verified."""
        user = UserFactory(username="testuser", email_verified=True)
        tasks.delete_non_verified_accounts()
        user = get_user_model().objects.filter(username="testuser")
        self.assertTrue(user.exists())
