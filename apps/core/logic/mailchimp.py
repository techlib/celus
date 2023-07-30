import json
import logging
import re
from typing import Dict, List, Optional, Set

import mailchimp_marketing as MailchimpMarketing
from allauth.account.models import EmailAddress
from django.conf import settings
from django.db.models import Exists, OuterRef, QuerySet
from mailchimp_marketing.api_client import ApiClientError

from core.models import User

logger = logging.getLogger(__name__)

CONSORTIAL_MANAGER = settings.MAILCHIMP_REASON_CONSORTIAL_MANAGER
NORMAL_USER = settings.MAILCHIMP_REASON_NORMAL_USER


class Field:
    FIRST_NAME = "FNAME"
    LAST_NAME = "LNAME"
    INSTALLATIONS = "MMERGE6"
    ADDR_1 = "MMERGE7"
    ADDR_2 = "MMERGE8"
    ADDR_3 = "MMERGE9"


def this_celus_domain():
    return settings.ALLOWED_HOSTS[0]


def domain_from_address(address) -> str:
    return re.sub(r'^https://|/$', '', address)


def address_from_domain(domain) -> Optional[str]:
    if domain:
        return f'https://{domain}/'
    return None


def celus_name_from_domain(domain: str) -> str:
    for key, value in settings.CELUS_CUSTOM_NAME_PAIRS.items():
        if value == domain:
            return key
    if domain.endswith('.celus.net'):
        celus_name = re.sub(r'\.celus\.net$', '', domain)
        if "." in celus_name:
            raise ValueError(
                f"Domain {domain} is not a valid Celus domain. "
                "No dot is allowed in the domain before the '.celus.net'."
            )
        return celus_name
    return domain


def domain_from_celus_name(celus_name: str) -> Optional[str]:
    if celus_name:
        return settings.CELUS_CUSTOM_NAME_PAIRS.get(
            celus_name, f"{celus_name}.celus.net" if "." not in celus_name else celus_name
        )
    return None


class Celus:
    def __init__(
        self,
        domain: Optional[str] = None,
        reasons: Optional[Set[str]] = None,
        is_in_addresses: bool = False,
    ):
        self.domain = domain if domain else this_celus_domain()
        self.reasons = reasons if reasons else set()
        self.is_preferred = (
            domain == domain_from_celus_name(settings.MAILCHIMP_PREFERRED_CELUS_NAME)
            if settings.MAILCHIMP_PREFERRED_CELUS_NAME
            else False
        )
        self.is_in_addresses: bool = is_in_addresses

    def name(self):
        return celus_name_from_domain(self.domain)

    def address(self):
        return address_from_domain(self.domain)

    def update_reasons(self, corresponding_celususer: User) -> bool:
        managed_reasons = {CONSORTIAL_MANAGER, NORMAL_USER}
        reasons = (
            {corresponding_celususer.mailchimp_user_reason()} if corresponding_celususer else set()
        )
        external_reasons = self.reasons - managed_reasons  # remember external reasons
        stored_reasons = self.reasons & managed_reasons  # compare only managed reasons
        if reasons != stored_reasons:
            self.reasons = reasons | external_reasons
            return True
        return False


class Member:
    def __init__(
        self,
        email: str,
        id: Optional[int] = None,
        first_name: str = "",
        last_name: str = "",
        first_celus: Optional[str] = None,
        celuses: Optional[Dict[str, str]] = None,
        tags: Optional[List[int]] = None,
    ):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.celuses = celuses if celuses else {}
        self.should_be_updated = False
        self.tags = tags if tags else []
        self.warnings = []
        self.first_celus = first_celus

    @classmethod
    def create_from_mailchimp_record(cls, record):
        member = cls(
            id=record["id"],
            email=record['email_address'],
            first_name=record["merge_fields"][Field.FIRST_NAME],
            last_name=record["merge_fields"][Field.LAST_NAME],
            tags=record["tags"],
        )
        member.parse_celus_installations(
            json.loads(record["merge_fields"][Field.INSTALLATIONS])
            if record["merge_fields"][Field.INSTALLATIONS]
            else []
        )
        member.parse_celus_addresses(
            [
                record["merge_fields"][Field.ADDR_1],
                record["merge_fields"][Field.ADDR_2],
                record["merge_fields"][Field.ADDR_3],
            ]
        )
        return member

    @classmethod
    def create_from_celususer(cls, celususer):
        member = cls(
            id=None,
            email=celususer.email,
            first_name=celususer.first_name,
            last_name=celususer.last_name,
        )
        member.add_this_celus(celususer)
        return member

    def should_be_deleted(self):
        if (
            settings.MAILCHIMP_DO_NOT_DELETE_TAG
            and settings.MAILCHIMP_DO_NOT_DELETE_TAG in self.tags
        ):
            return False
        return not self.celuses

    def parse_celus_installations(self, celus_installations):

        for installation in celus_installations:
            domain = domain_from_celus_name(installation['name'])
            reason = installation['reason']
            if domain not in self.celuses:
                new_celus = Celus(domain=domain, reasons={reason})
                self.celuses[domain] = new_celus
            elif reason not in self.celuses[domain].reasons:
                self.celuses[domain].reasons.add(reason)

    def parse_celus_addresses(self, celus_addresses):
        if celus_addresses != sorted(celus_addresses, key=lambda x: x != "", reverse=True):
            self.should_be_updated = True

        for address in celus_addresses:
            if address:
                domain = domain_from_address(address)
                if domain in self.celuses:
                    self.celuses[domain].is_in_addresses = True
                else:
                    self.celuses[domain] = Celus(domain=domain, is_in_addresses=True)
                    self.should_be_updated = True
        for address in celus_addresses:
            if address:
                self.first_celus = domain_from_address(address)
                break

    def celuses_in_addresses(self):
        return [celus for celus in self.celuses.values() if celus.is_in_addresses]

    def add_this_celus(self, celususer):
        reasons = {celususer.mailchimp_user_reason()}
        celus = Celus(reasons=reasons, is_in_addresses=True)
        self.celuses[celus.domain] = celus

    def update_celus_in_addresses(self, celus, celususer):
        updated = False
        if celususer:
            if not celus.is_in_addresses:
                if len(self.celuses_in_addresses()) > 2 and (
                    not settings.MAILCHIMP_STAFF_TAG
                    or settings.MAILCHIMP_STAFF_TAG not in self.tags
                ):
                    self.warnings.append(
                        Warning(
                            self.email,
                            "member is user in more than 3 celuses",
                            "This member, who is not tagged as 'staff', "
                            "is user in more than 3 celuses, "
                            "therefore not all Celus addresses of his "
                            "will be displayed in the Mailchimp celus address col.",
                        )
                    )
                if len(self.celuses_in_addresses()) < 3 or celus.is_preferred:
                    celus.is_in_addresses = True
                    updated = True
        else:
            if celus.is_in_addresses:
                celus.is_in_addresses = False
                updated = True
        return updated

    def update(self, celususer):
        """
        Check for discrepancies and make the necessary corrections.
        Returns True if any changes were made, False otherwise.
        """
        # update first name and last name
        if celususer:
            if celususer.first_name and not self.first_name:
                self.first_name = celususer.first_name
                self.should_be_updated = True
            if celususer.last_name and not self.last_name:
                self.last_name = celususer.last_name
                self.should_be_updated = True

        # update celuses
        this_celus = self.celuses.get(this_celus_domain())
        if this_celus:
            # update celus reasons
            if this_celus.update_reasons(celususer):
                self.should_be_updated = True

            # update celus in celus-address column
            if self.update_celus_in_addresses(this_celus, celususer):
                self.should_be_updated = True

            # remove empty celus
            if not this_celus.reasons and not this_celus.is_in_addresses:
                self.celuses.pop(this_celus.domain)
                self.should_be_updated = True

        elif celususer:
            # add this missing celus
            self.add_this_celus(celususer)
            self.should_be_updated = True

        # update first_celus
        if preferred_domain := domain_from_celus_name(settings.MAILCHIMP_PREFERRED_CELUS_NAME):
            if preferred_domain in self.celuses and self.first_celus != preferred_domain:
                self.first_celus = preferred_domain
                self.should_be_updated = True

    def create_addresses(self):
        celuses = self.celuses_in_addresses()

        # sort celuses by first_celus
        celuses.sort(key=lambda x: x.domain == self.first_celus, reverse=True)
        return [celus.address() for celus in celuses[:3]]

    def create_installations(self):

        celus_reason_pairs = [
            {"name": celus.name(), "reason": reason}
            for celus in self.celuses.values()
            for reason in celus.reasons
        ]

        # sort celus_reason_pairs by first_celus and reason
        def sort_key(record):
            return (
                domain_from_celus_name(record["name"]) == self.first_celus,
                record["reason"] in {CONSORTIAL_MANAGER, NORMAL_USER},
            )

        celus_reason_pairs.sort(key=sort_key, reverse=True)

        # filter out records which are too long
        filtered_installations = []
        temp_installations = []
        for record in celus_reason_pairs:
            temp_installations.append(record)
            if len(json.dumps(temp_installations)) < 253:
                filtered_installations.append(record)
            else:
                if (
                    not settings.MAILCHIMP_STAFF_TAG
                    or settings.MAILCHIMP_STAFF_TAG not in self.tags
                ):
                    self.warnings.append(
                        Warning(
                            self.email,
                            "celus installations value too long",
                            "This member who is not tagged as 'staff' couldn't be fully updated. "
                            "Content of Celus Installations column for this member is longer than "
                            "253 characters, adjust the content by removing whole record separated "
                            "by { }, so that the length doesn't exceed 253 characters. "
                            "When doing so, try to avoid removing those records which contain "
                            f'"reason":"{NORMAL_USER}" or "reason":"{CONSORTIAL_MANAGER}".',
                        )
                    )
                break

        return json.dumps(filtered_installations)

    def create_merge_fields(self):
        addresses = self.create_addresses()
        return {
            Field.FIRST_NAME: self.first_name,
            Field.LAST_NAME: self.last_name,
            Field.INSTALLATIONS: self.create_installations(),
            Field.ADDR_1: addresses[0] if len(addresses) > 0 else "",
            Field.ADDR_2: addresses[1] if len(addresses) > 1 else "",
            Field.ADDR_3: addresses[2] if len(addresses) > 2 else "",
        }

    def create_data(self):
        return {
            "email_address": self.email,
            "status": "subscribed",
            "merge_fields": self.create_merge_fields(),
        }


class Warning:
    def __init__(self, email: str, title: str, detail: str):
        self.email = email
        self.title = title
        self.detail = detail


class Error:
    def __init__(self, email: str, title: str, detail: str):
        self.email = email
        self.title = title
        self.detail = detail


class SyncTask:
    def __init__(self):
        self.members_data = []
        self.all_members_emails = set()
        self.parsed_members = set()
        self.errors = []
        self.warnings = []
        self.updated_members_emails = []
        self.added_members_emails = []
        self.deleted_members_emails = []
        self.client = MailchimpMarketing.Client()
        self.client.set_config(
            {"api_key": settings.MAILCHIMP_API_KEY, "server": settings.MAILCHIMP_SERVER_PREFIX}
        )
        self.celususers_in_audience_dict: Optional[Dict[str, User]] = None
        self.celususers_not_in_audience: Optional[QuerySet[User]] = None

    def add_member(self, celususer):
        member = Member.create_from_celususer(celususer)
        self.warnings += member.warnings
        logger.info("adding member %s", member.email)
        self.client.lists.add_list_member(settings.MAILCHIMP_AUDIENCE_ID, member.create_data())

    def add_new_members(self):
        for celususer in self.celususers_not_in_audience:
            try:
                self.add_member(celususer)
                self.added_members_emails.append(celususer.email)
            except ApiClientError as e:
                self.errors.append(Error(celususer.email, "ApiClientError", e.text))

    def update_member(self, member):
        data = {"merge_fields": member.create_merge_fields()}
        self.warnings += member.warnings
        logger.info("updating member %s", member.email)
        self.client.lists.update_list_member(settings.MAILCHIMP_AUDIENCE_ID, member.id, data)

    def delete_member(self, member):
        logger.info("deleting member %s", member.email)
        self.client.lists.delete_list_member(settings.MAILCHIMP_AUDIENCE_ID, member.id)

    def update_or_delete_members(self):
        self.deleted_members_emails = []
        for member in self.parsed_members:
            celususer = self.celususers_in_audience_dict.get(member.email)
            member.update(celususer)
            self.warnings += member.warnings
            if member.should_be_deleted():
                try:
                    self.delete_member(member)
                    self.deleted_members_emails.append(member.email)
                except ApiClientError as e:
                    self.errors.append(Error(celususer.email, "ApiClientError", e.text))

            if member.should_be_updated:
                try:
                    self.update_member(member)
                    self.updated_members_emails.append(member.email)
                except ApiClientError as e:
                    self.errors.append(Error(celususer.email, "ApiClientError", e.text))
                    self.warnings += member.self.warnings

    def parse_members_data(self):
        for member in self.members_data:
            email = member["email_address"]
            self.all_members_emails.add(email)
            try:
                new_member = Member.create_from_mailchimp_record(member)
                self.parsed_members.add(new_member)
            except ValueError as e:
                self.errors.append(
                    Error(
                        email, "ValueError", f"Could not parse this Mailchimp audience member: {e}"
                    )
                )

    def get_all_relevant_celususers(self):
        all_relevant_celususers = User.objects.filter(is_active=True)
        if settings.ALLOW_USER_REGISTRATION and not settings.ALLOW_EDUID_LOGIN:
            verified_email_address = EmailAddress.objects.filter(user=OuterRef('pk'), verified=True)
            all_relevant_celususers = all_relevant_celususers.annotate(
                has_verified_email=Exists(verified_email_address)
            ).filter(has_verified_email=True)

        celususers_in_audience = all_relevant_celususers.filter(email__in=self.all_members_emails)
        self.celususers_in_audience_dict = {user.email: user for user in celususers_in_audience}
        self.celususers_not_in_audience = all_relevant_celususers.difference(celususers_in_audience)

    def fetch_members_from_mailchimp(self):
        try:
            response = self.client.lists.get_list_members_info(
                settings.MAILCHIMP_AUDIENCE_ID, count=1000
            )
        except ApiClientError as e:
            error = Error("None", "ApiClientError", e.text)
            self.errors.append(error)
            response = None
        if not response or "members" not in response or not response["members"]:
            error = Error(
                "None",
                "no member from Mailchimp fetched",
                f"Celus {settings.ALLOWED_HOSTS[0]} "
                "was not able to fetch any member from Mailchimp.",
            )
            self.errors.append(error)
        else:
            self.members_data = response["members"]

    def create_report_email(self):

        if not settings.MAILCHIMP_ADMINS or not any(
            [
                self.added_members_emails,
                self.updated_members_emails,
                self.deleted_members_emails,
                self.warnings,
                self.errors,
            ]
        ):
            return None

        def build_email_body(section_name, email_list):
            sorted_emails = sorted(email_list)
            body = f"\n\n\n{section_name} members:\n" + "\n".join(sorted_emails)
            return body

        celus_name = celus_name_from_domain(this_celus_domain())
        address = address_from_domain(this_celus_domain())

        subject = f"Summary of Celus({celus_name})-MailChimp synchronization"
        subject += " with ERROR" if self.errors else ""

        body = (
            f"Celus {celus_name} ({address}) ran synchronization with MailChimp \n\n"
            f"Summary:\n"
            f"{len(self.added_members_emails)} Mailchimp contacts were ADDED from this Celus\n"
            f"{len(self.updated_members_emails)} Mailchimp contacts were UPDATED by this Celus\n"
            f"{len(self.deleted_members_emails)} Mailchimp contacts were DELETED by this Celus\n"
            f"{len(self.errors)} ERRORS occurred during the synchronization\n"
            f"{len(self.warnings)} WARNINGS occurred during the synchronization"
        )

        if self.errors:
            body += "\n\n\nERRORS:"
            for error in self.errors:
                body += f"\n\n{error.email}\n{error.title}\n{error.detail}"

        if self.warnings:
            body += "\n\n\nWARNINGS:"
            for warning in self.warnings:
                body += f"\n\n{warning.email}\n{warning.title}\n{warning.detail}"

        if self.added_members_emails:
            body += build_email_body("ADDED", self.added_members_emails)

        if self.updated_members_emails:
            body += build_email_body("UPDATED", self.updated_members_emails)

        if self.deleted_members_emails:
            body += build_email_body("DELETED", self.deleted_members_emails)
        return {"subject": subject, "body": body}
