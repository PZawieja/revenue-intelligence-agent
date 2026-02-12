select *
from {{ ref('dm_account_overview') }}
where account_name = 'Acme GmbH'
