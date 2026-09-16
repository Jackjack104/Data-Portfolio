with ranked as (
    select
        *,
        row_number() over (
            partition by company_id
            order by source_updated_at desc, ingested_at desc, raw_id desc
        ) as record_rank
    from {{ source('raw', 'crm_companies') }}
)

select
    company_id,
    company_name,
    {{ normalize_company_name('company_name') }} as normalized_company_name,
    {{ normalize_domain('domain') }} as normalized_domain,
    phone,
    address,
    city,
    upper(state) as state,
    postal_code,
    owner_id,
    nullif(erp_customer_id, '') as erp_customer_id,
    source_updated_at,
    batch_id,
    ingested_at
from ranked
where record_rank = 1
