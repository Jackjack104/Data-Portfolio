select
    md5('contact|' || contacts.contact_id) as contact_key,
    contacts.contact_id,
    customers.customer_key,
    contacts.company_id as crm_company_id,
    contacts.first_name,
    contacts.last_name,
    contacts.email,
    contacts.email_domain,
    contacts.phone,
    contacts.job_title
from {{ ref('stg_crm_contacts') }} as contacts
left join {{ ref('dim_customer') }} as customers
    on contacts.company_id = customers.crm_company_id
