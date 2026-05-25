-- RetailIQ — Supabase Setup
-- Run once in Supabase SQL Editor

create table if not exists data_batches (
    id text primary key,
    label text,
    filename text,
    date_min text,
    date_max text,
    row_count integer,
    storage_path text,
    created_at text
);

create table if not exists users (
    id bigserial primary key,
    name text unique not null
);

create table if not exists user_customers (
    user_id bigint references users(id) on delete cascade,
    customer_num text,
    primary key (user_id, customer_num)
);

-- Storage bucket (run in Supabase dashboard or via API)
-- Create bucket named: salesiq (private)
-- Then add RLS policy:
insert into storage.buckets (id, name, public) values ('salesiq', 'salesiq', false)
on conflict do nothing;

create policy "service role full access"
on storage.objects for all
using (bucket_id = 'salesiq');
