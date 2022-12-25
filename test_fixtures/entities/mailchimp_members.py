import factory


class Member:
    def __init__(
        self,
        id,
        first_name,
        last_name,
        email="",
        celus_installations=None,
        celus_address1="",
        celus_address2="",
        celus_address3="",
        tags=None,
    ):
        self.email = email
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        # MMERGE6
        self.celus_installations = celus_installations if celus_installations else []
        # MMERGE7
        self.celus_address1 = celus_address1
        # MMERGE8
        self.celus_address2 = celus_address2
        # MMERGE9
        self.celus_address3 = celus_address3
        self.tags = tags if tags else []
        self.perform = None


class MemberFactory(factory.Factory):
    class Meta:
        model = Member

    id = factory.Faker('uuid4')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = "user@celus.test"
