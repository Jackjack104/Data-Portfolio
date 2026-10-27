{% macro normalize_company_name(column_name) -%}
trim(
    regexp_replace(
        regexp_replace(
            lower(replace(coalesce({{ column_name }}, ''), '&', ' and ')),
            '\m(llc|inc|incorporated|corp|corporation|company|co|pllc|pa)\M',
            ' ',
            'g'
        ),
        '[^a-z0-9]+',
        ' ',
        'g'
    )
)
{%- endmacro %}

{% macro normalize_domain(column_name) -%}
nullif(
    regexp_replace(
        regexp_replace(lower(trim(coalesce({{ column_name }}, ''))), '^https?://', ''),
        '^www\.',
        ''
    ),
    ''
)
{%- endmacro %}
