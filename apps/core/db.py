from django.db.models import CharField, Lookup, TextField


@TextField.register_lookup
@CharField.register_lookup
class ILike(Lookup):
    """
    Custom lookup that uses ILIKE on Postgres which is much faster than the default approach
    when using a TRGM index
    """

    lookup_name = 'ilike'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"{lhs} ILIKE CONCAT('%%', {rhs}, '%%')", params
