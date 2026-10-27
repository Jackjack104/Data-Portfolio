with match_candidates as (
    select
        crm.company_id as crm_company_id,
        erp.customer_id as erp_customer_id,
        'external_id'::text as match_method,
        100::integer as match_confidence
    from {{ ref('stg_crm_companies') }} as crm
    inner join {{ ref('stg_erp_customers') }} as erp
        on crm.erp_customer_id = erp.customer_id

    union all

    select
        crm.company_id,
        erp.customer_id,
        'domain'::text as match_method,
        90::integer as match_confidence
    from {{ ref('stg_crm_companies') }} as crm
    inner join {{ ref('stg_erp_customers') }} as erp
        on crm.normalized_domain = erp.normalized_domain
        and crm.normalized_domain is not null

    union all

    select
        crm.company_id,
        erp.customer_id,
        'normalized_name_and_state'::text as match_method,
        85::integer as match_confidence
    from {{ ref('stg_crm_companies') }} as crm
    inner join {{ ref('stg_erp_customers') }} as erp
        on crm.normalized_company_name = erp.normalized_company_name
        and crm.state = erp.state
),

ranked as (
    select
        *,
        row_number() over (
            partition by crm_company_id
            order by match_confidence desc, erp_customer_id
        ) as match_rank
    from match_candidates
)

select
    crm_company_id,
    erp_customer_id,
    match_method,
    match_confidence
from ranked
where match_rank = 1
