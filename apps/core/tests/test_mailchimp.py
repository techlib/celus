import json
from unittest import mock

import pytest  # noqa

from core.fake_data import MemberFactory, UserFactory
from core.logic.mailchimp import (
    Celus,
    Error,
    Field,
    Warning,
    address_from_domain,
    celus_name_from_domain,
    domain_from_address,
    domain_from_celus_name,
)
from core.models import User
from core.tasks import sync_mailchimp_contacts_with_celus_task
from test_scenarios.basic import basic1  # noqa


def merge_fields(member_case):
    return {
        Field.FIRST_NAME: member_case.first_name,
        Field.LAST_NAME: member_case.last_name,
        Field.INSTALLATIONS: json.dumps(member_case.celus_installations),
        Field.ADDR_1: member_case.celus_address1 if member_case.celus_address1 else '',
        Field.ADDR_2: member_case.celus_address2 if member_case.celus_address2 else '',
        Field.ADDR_3: member_case.celus_address3 if member_case.celus_address3 else '',
    }


def create_add_member_data(member):
    return {
        'email_address': member.email,
        'status': 'subscribed',
        'merge_fields': merge_fields(member),
    }


def create_fetched_data(member_case):
    return {
        'id': member_case.id,
        'email_address': member_case.email,
        'merge_fields': merge_fields(member_case),
        'tags': member_case.tags,
    }


class TestMembersHandling:
    @pytest.mark.parametrize(
        "address, expected_result",
        [
            ("https://example.celus.net/", "example.celus.net"),
            ("https://run.celus.one/", "run.celus.one"),
            ("https://www.example.celus.net/", "www.example.celus.net"),
        ],
    )
    def test_domain_from_address(self, address, expected_result):
        assert domain_from_address(address) == expected_result

    @pytest.mark.parametrize(
        "domain, custom_name_pair, expected_result, value_error",
        [
            ("foo.celus.net", {}, "foo", False),
            ("bar-foo.celus.net", {}, "bar-foo", False),
            ("bar.foo.net", {}, "bar.foo.net", False),
            ("bar.foo.celus.net", {}, None, True),
            ("run.celus.one", {"K1": "run.celus.one"}, "K1", False),
        ],
    )
    def test_celus_name_from_domain(
        self, domain, custom_name_pair, expected_result, settings, value_error
    ):
        settings.CELUS_CUSTOM_NAME_PAIRS = custom_name_pair
        if value_error:
            with pytest.raises(ValueError):
                celus_name_from_domain(domain)
        else:
            assert celus_name_from_domain(domain) == expected_result

    @pytest.mark.parametrize(
        "celus_name, custom_name_pair, expected_result",
        [
            ("foo", {}, "foo.celus.net"),
            ("foo-bar", {}, "foo-bar.celus.net"),
            ("bar.foo", {}, "bar.foo"),
            ("K1", {"K1": "run.celus.one"}, "run.celus.one"),
            ("", {}, None),
            ("", {"K1": "run.celus.one"}, None),
        ],
    )
    def test_domain_from_celus_name(self, celus_name, custom_name_pair, expected_result, settings):
        settings.CELUS_CUSTOM_NAME_PAIRS = custom_name_pair
        assert domain_from_celus_name(celus_name) == expected_result

    @pytest.mark.parametrize(
        "domain, expected_result",
        [
            ("example.com", "https://example.com/"),
            ("www.example.com", "https://www.example.com/"),
            ("", None),
        ],
    )
    def test_address_from_domain(self, domain, expected_result):
        assert address_from_domain(domain) == expected_result

    @pytest.mark.parametrize(
        [
            'any_member_fetched',
            'corresponding_member_exists',
            'member_parsed',
            'add_member_call_count',
        ],
        [
            [True, True, True, 0],
            [True, True, False, 0],
            [True, False, False, 1],
            [False, False, False, 0],
        ],
    )
    @pytest.mark.django_db
    def test_adding_members(
        self,
        settings,
        member_parsed,
        any_member_fetched,
        corresponding_member_exists,
        add_member_call_count,
    ):
        settings.ALLOWED_HOSTS = ['this.celus.net']
        user = UserFactory()

        fetched_members = []
        if any_member_fetched:
            fetched_members.append(
                create_fetched_data(MemberFactory(email='some_other_member@celus.test'))
            )
        if corresponding_member_exists:
            member = create_fetched_data(MemberFactory(email=user.email))
            if not member_parsed:
                member['merge_fields'][Field.INSTALLATIONS] = ']}'
            fetched_members.append(member)
        else:
            member_to_be_added = MemberFactory(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                celus_installations=[{'name': 'this', 'reason': 'normal user'}],
                celus_address1='https://this.celus.net/',
            )
            response = create_add_member_data(member_to_be_added)

        with mock.patch('mailchimp_marketing.Client') as MockClient:
            MockClient.return_value.lists.get_list_members_info.return_value = {
                "members": fetched_members
            }

            sync_mailchimp_contacts_with_celus_task()

            assert MockClient.return_value.lists.add_list_member.call_count == add_member_call_count

            if add_member_call_count:
                assert (
                    MockClient.return_value.lists.add_list_member.call_args_list[0][0][1]
                    == response
                )

    @pytest.mark.parametrize(
        ['test_case', 'correspond_celususer_exists', 'delete_member_call_count'],
        [
            ['this_normuser_reason', False, 1],
            ['this_consman_reason', False, 1],
            ['other_normuser_reason', False, 0],
            ['other_consman_reason', False, 0],
            ['this_whatever', False, 0],
            ['other_whatever_reason', False, 0],
            ['no_reason_randomtag', False, 1],
            ['no_reason_donotdeletetag', False, 0],
            ['no_reason', True, 0],
            ['no_reason', False, 1],
        ],
    )
    @pytest.mark.django_db
    def test_deleting_members(
        self,
        settings,
        test_case,
        correspond_celususer_exists,
        delete_member_call_count,
        delete_member_test_cases,
    ):
        if correspond_celususer_exists:
            UserFactory(email='user@celus.test')

        with mock.patch('mailchimp_marketing.Client') as MockClient:
            settings.ALLOWED_HOSTS = ['this.celus.net']

            MockClient.return_value.lists.get_list_members_info.return_value = {
                "members": [create_fetched_data(delete_member_test_cases[test_case])]
            }

            sync_mailchimp_contacts_with_celus_task()
            MockClient.return_value.lists.get_list_members_info.assert_called_once()
            assert (
                MockClient.return_value.lists.delete_list_member.call_count
                == delete_member_call_count
            )

            if delete_member_call_count:
                assert (
                    MockClient.return_value.lists.delete_list_member.call_args_list[0][0][1]
                    == delete_member_test_cases[test_case].id
                )

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ['test_case_member_pair', 'test_case_celususer', 'this_celus'],
        [
            ['update_firstnam', 'firstnam_lastnam', 'this'],
            ['update_lastnam', 'firstnam_lastnam', 'this'],
            ['update_firstnam_lastnam', 'firstnam_lastnam', 'this'],
            ['no_update_normuser', 'normuser', 'this'],
            ['no_update_consman', 'consman', 'this'],
            ['update_usertype_to_normuser', 'normuser', 'this'],
            ['update_usertype_to_consman', 'consman', 'this'],
            ['add_usertype_normuser', 'normuser', 'this'],
            ['add_usertype_consman', 'consman', 'this'],
            ['remove_this_normuser_still_other_normuser', None, 'this'],
            ['remove_this_consman_still_other_consman', None, 'this'],
            ['remove_this_normuser_still_this_whatever', None, 'this'],
            ['remove_this_normuser_still_other_whatever', None, 'this'],
            ['add_this_normuser_remove_toolongreason', 'normuser', 'this'],
            ['add_this_normuser_remove_toolongreason_warn', 'normuser', 'this'],
            ['update_firstnam_lastnam_install_addrs', 'firstnam_lastnam', 'this'],
            ['add_addrs', 'normuser', 'this'],
            ['remove_addrs_keep_this_whatever', None, 'this'],
            ['remove_addrs_keep_other_whatever', None, 'this'],
            ['first_to_last_empty_addrs', 'normuser', 'this'],
            ['second_to_last_empty_addrs', 'normuser', 'this'],
            ['third_to_first_pref_addrs', 'normuser', 'this'],
            ['second_to_first_pref_addrs', 'normuser', 'this'],
            ['cannt_add_more_addrs', 'normuser', 'this'],
            ['cannt_add_more_addrs_warn', 'normuser', 'this'],
            ['cannt_add_more_addrs_pref_added', 'normuser', 'pref'],
            ['cannt_add_more_addrs_pref_added_warn', 'normuser', 'pref'],
        ],
    )
    def test_updating_members(
        self,
        test_case_member_pair,
        test_case_celususer,
        update_member_test_cases,
        settings,
        celususers,
        this_celus,
        celus_domains,
    ):

        settings.ALLOWED_HOSTS = [celus_domains[this_celus]]
        settings.MAILCHIMP_ADMINS = ['example-admin@email.com']
        test_case = update_member_test_cases[test_case_member_pair]
        fetched_member = create_fetched_data(test_case['tested'])
        if test_case_celususer:
            celususer = celususers[test_case_celususer]
            User.objects.exclude(email=celususer.email).delete()
            celususer.email = fetched_member['email_address']
            celususer.save()

        with mock.patch('mailchimp_marketing.Client') as MockClient, mock.patch(
            "core.tasks.async_mail_mailchimp_admins"
        ) as MockAsyncMail:
            MockClient.return_value.lists.get_list_members_info.return_value = {
                'members': [fetched_member]
            }
            sync_mailchimp_contacts_with_celus_task()
            if 'result' in test_case:
                MockClient.return_value.lists.update_list_member.assert_called_once()
                member_updated_data = {'merge_fields': merge_fields(test_case['result'])}
                assert MockClient.return_value.lists.update_list_member.call_args_list[0][0] == (
                    settings.MAILCHIMP_AUDIENCE_ID,
                    test_case['tested'].id,
                    member_updated_data,
                )
            else:
                MockClient.return_value.lists.update_list_member.assert_not_called()

            if {"warning", "result", "error"}.intersection(test_case.keys()):
                # Check if the report email was sent and check the emil subject
                MockAsyncMail.delay.assert_called_once()
                assert (
                    f'Summary of Celus({celus_name_from_domain(celus_domains[this_celus])})'
                    '-MailChimp synchronization' in MockAsyncMail.delay.call_args_list[0][0][0]
                )

                # Check for warnings in the email
                if "warning" in test_case:
                    assert test_case["warning"] in MockAsyncMail.delay.call_args_list[0][0][1]
                else:
                    assert "WARNINGS:" not in MockAsyncMail.delay.call_args_list[0][0][1]

                # Check for errors in the email
                if "error" in test_case:
                    assert (
                        'synchronization with ERROR' in MockAsyncMail.delay.call_args_list[0][0][0]
                    )
                    assert test_case["error"] in MockAsyncMail.delay.call_args_list[0][0][1]
                else:
                    assert (
                        'synchronization with ERROR'
                        not in MockAsyncMail.delay.call_args_list[0][0][0]
                    )
                    assert "ERRORS:" not in MockAsyncMail.delay.call_args_list[0][0][1]
            else:
                MockAsyncMail.delay.assert_not_called()


class TestWarning:
    @pytest.mark.parametrize(
        ["email", "title", "detail"],
        [
            ("example@example.com", "Warning Title 1", "Warning detail message 1"),
            ("test@test.com", "Title 2", "Detail message 2"),
            (
                "user@gmail.com",
                "Warning Title 3",
                "This is a long detailed error message "
                "that should be able to handle multiple lines and characters",
            ),
        ],
    )
    def test_warning_init(self, email, title, detail):
        w = Warning(email, title, detail)
        assert w.email == email
        assert w.title == title
        assert w.detail == detail


class TestError:
    @pytest.mark.parametrize(
        ["email", "title", "detail"],
        [
            ("example@example.com", "Error Title 1", "Error detail message 1"),
            ("test@test.com", "Title 2", "Detail message 2"),
            (
                "user@gmail.com",
                "Error Title 3",
                "This is a long detailed error message "
                "that should be able to handle multiple lines and characters",
            ),
        ],
    )
    def test_error_init(self, email, title, detail):
        e = Error(email, title, detail)
        assert e.email == email
        assert e.title == title
        assert e.detail == detail

    @pytest.mark.django_db
    def test_no_member_fetched_error(self, settings):
        settings.MAILCHIMP_ADMINS = ['example-admin@email.com']

        with mock.patch('mailchimp_marketing.Client') as MockClient, mock.patch(
            "core.tasks.async_mail_mailchimp_admins"
        ) as MockAsyncMail:

            MockClient.return_value.lists.get_list_members_info.return_value = {}
            sync_mailchimp_contacts_with_celus_task()
            MockAsyncMail.delay.assert_called_once()
            assert 'synchronization with ERROR' in MockAsyncMail.delay.call_args_list[0][0][0]
            assert "no member from Mailchimp fetched" in MockAsyncMail.delay.call_args_list[0][0][1]

    @pytest.mark.django_db
    def test_member_not_parsable_error(self, settings):
        settings.MAILCHIMP_ADMINS = ['example-admin@email.com']

        with mock.patch('mailchimp_marketing.Client') as MockClient, mock.patch(
            "core.tasks.async_mail_mailchimp_admins"
        ) as MockAsyncMail:
            member = create_fetched_data(MemberFactory())
            member['merge_fields'][Field.INSTALLATIONS] = ']}'
            fetched_members = [member]
            MockClient.return_value.lists.get_list_members_info.return_value = {
                "members": fetched_members
            }
            sync_mailchimp_contacts_with_celus_task()
            MockAsyncMail.delay.assert_called_once()
            assert 'synchronization with ERROR' in MockAsyncMail.delay.call_args_list[0][0][0]
            assert (
                "Could not parse this Mailchimp audience member"
                in MockAsyncMail.delay.call_args_list[0][0][1]
            )

    @pytest.mark.django_db
    def test_handling_api_client_error(self, settings):
        settings.SYNC_USERS_TO_MAILCHIMP = True
        settings.MAILCHIMP_ADMINS = ['example-admin@email.com']
        settings.MAILCHIMP_API_KEY = ''
        settings.MAILCHIMP_SERVER_PREFIX = ''
        settings.MAILCHIMP_AUDIENCE_ID = ''
        with mock.patch("core.tasks.async_mail_mailchimp_admins") as MockAsyncMail:
            sync_mailchimp_contacts_with_celus_task()
            MockAsyncMail.delay.assert_called_once()
            assert 'synchronization with ERROR' in MockAsyncMail.delay.call_args_list[0][0][0]
            assert "ApiClientError" in MockAsyncMail.delay.call_args_list[0][0][1]
            assert "no member from Mailchimp fetched" in MockAsyncMail.delay.call_args_list[0][0][1]


class TestCelus:
    @pytest.mark.parametrize(
        [
            'tested_domain',
            'tested_reasons',
            'expected_domain',
            'expected_reasons',
            'expected_is_preferred',
        ],
        [
            ['preferredcelus.celus.net', None, 'preferredcelus.celus.net', set(), True],
            [
                'example.celus.net',
                {'reason1', 'reason2'},
                'example.celus.net',
                {'reason1', 'reason2'},
                False,
            ],
            [None, None, 'this.celus.net', set(), False],
        ],
    )
    def test_celus_init(
        self,
        tested_domain,
        tested_reasons,
        expected_domain,
        expected_reasons,
        expected_is_preferred,
        settings,
    ):
        settings.MAILCHIMP_PREFERRED_CELUS_NAME = 'preferredcelus'
        settings.ALLOWED_HOSTS = ['this.celus.net']
        celus = Celus(domain=tested_domain, reasons=tested_reasons)
        assert celus.domain == expected_domain
        assert celus.reasons == expected_reasons
        assert celus.is_preferred == expected_is_preferred

    @pytest.mark.parametrize(
        "domain, custom_name_pair, expected_result",
        [
            ("example.celus.net", {}, "example"),
            ("example.com", {}, "example.com"),
            ("run.celus.one", {'K1': 'run.celus.one'}, 'K1'),
            (None, {}, 'this'),
        ],
    )
    def test_name_method(self, domain, custom_name_pair, expected_result, settings):
        with mock.patch("core.logic.mailchimp.this_celus_domain") as this_celus_domain:
            this_celus_domain.return_value = 'this.celus.net'
            settings.CELUS_CUSTOM_NAME_PAIRS = custom_name_pair
            celus = Celus(domain=domain)
            assert celus.name() == expected_result

    @pytest.mark.parametrize(
        "domain, expected",
        [
            ("celus.net", "https://celus.net/"),
            ("preferred_domain.com", "https://preferred_domain.com/"),
        ],
    )
    def test_address_method(self, domain, expected):
        celus = Celus(domain=domain)
        assert celus.address() == expected

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "corresponding_celususer, reasons, user, expected_reasons, expected_result",
        [
            (True, set(), 'master_admin', {'consortial manager'}, True),
            (True, set(), 'user1', {'normal user'}, True),
            (True, {'normal user'}, 'master_admin', {'consortial manager'}, True),
            (True, {'consortial manager'}, 'user1', {'normal user'}, True),
            (True, {'foo'}, 'user1', {'foo', 'normal user'}, True),
            (True, {'foo'}, 'master_admin', {'foo', 'consortial manager'}, True),
            (False, set(), 'master_admin', set(), False),
            (False, set(), 'user1', set(), False),
            (False, {'normal user'}, 'master_admin', set(), True),
            (False, {'consortial manager'}, 'user1', set(), True),
            (False, {'foo'}, 'user1', {'foo'}, False),
            (False, {'foo'}, 'master_admin', {'foo'}, False),
            # reason 'foo' represents any arbitrary reason which
            # can be created by editor of the MailChimp audience
        ],
    )
    def test_if_update_reasons(
        self,
        corresponding_celususer,
        reasons,
        user,
        expected_reasons,
        expected_result,
        settings,
        basic1,
    ):
        settings.MAILCHIMP_REASON_NORMAL_USER = 'normal user'
        settings.MAILCHIMP_REASON_CONSORTIAL_MANAGER = 'consortial manager'
        celus = Celus(reasons=reasons)
        if corresponding_celususer:
            celususer = basic1['users'][user]
        else:
            celususer = None
        assert celus.update_reasons(celususer) == expected_result
        assert celus.reasons == expected_reasons
