with erp_customers as (
    select
        erp.customer_id as erp_customer_id,
        matches.crm_company_id,
        erp.company_name as customer_name,
        erp.normalized_domain,
        erp.address,
        erp.city,
        erp.state,
        erp.postal_code,
        crm.owner_id,
        erp.is_active,
        matches.match_method,
        matches.match_confidence
    from {{ ref('stg_erp_customers') }} as erp
    left join {{ ref('int_company_matches') }} as matches
        on erp.customer_id = matches.erp_customer_id
    left join {{ ref('stg_crm_companies') }} as crm
        on matches.crm_company_id = crm.company_id
),

crm_only as (
    select
        null::text as erp_customer_id,
        crm.company_id as crm_company_id,
        crm.company_name as customer_name,
        crm.normalized_domain,
        crm.address,
        crm.city,
        crm.state,
        crm.postal_code,
        crm.owner_id,
        null::boolean as is_active,
        'unmatched_crm'::text as match_method,
        0::integer as match_confidence
    from {{ ref('stg_crm_companies') }} as crm
    left join {{ ref('int_company_matches') }} as matches
        on crm.company_id = matches.crm_company_id
    where matches.crm_company_id is null
),

combined as (
    select * from erp_customers
    union all
    select * from crm_only
)

select
    md5(
        case
            when erp_customer_id is not null then 'erp|' || erp_customer_id
            else 'crm|' || crm_company_id
        end
    ) as customer_key,
    erp_customer_id,
    crm_company_id,
    customer_name,
    normalized_domain,
    address,
    city,
    state,
    postal_code,
    owner_id,
    is_active,
    match_method,
    match_confidence
from combined
