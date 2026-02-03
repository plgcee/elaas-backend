# Supabase table: workshops
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py
#
# Migration: add column template_group_id uuid REFERENCES template_groups(id) NULL;
# Then template_id becomes nullable for group workshops.

"""
Expected Supabase table structure:
- id: uuid (primary key)
- name: text (not null)
- description: text (nullable)
- template_id: uuid (foreign key to templates.id, nullable) - used for single-template workshops; null when template_group_id is set
- template_group_id: uuid (foreign key to template_groups.id, nullable) - when set, this workshop deploys all templates in the group
- user_id: uuid (foreign key to users.id, not null)
- environment_id: uuid (foreign key to environments.id, nullable) - logical isolation
- terraform_vars: jsonb (nullable) - for group workshops: keyed by template_id, e.g. {"<template_id>": {"var": "..."}}
- status: text (not null, default: 'pending') - values: pending, deploying, deployed, failed, destroying
- fargate_task_arn: text (nullable)
- deployment_output: jsonb (nullable)
- ttl_hours: number (nullable)
- expires_at: timestamp (nullable)
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)
"""
