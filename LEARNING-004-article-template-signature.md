# LEARNING-004: Article Template — Missing Signature Image

## Date
March 17, 2026

## Problem
Paper 012 (day-012.html) displayed broken image alt text "David Solomon signature" instead of the actual signature image. The `<img src="assets/signature.png">` tag referenced a file that did not exist in the TR2 repository.

## Root Cause
During the migration from the V1 repository (trainingrun-site) to the TR2 repository, the `assets/signature.png` file was never migrated. The HTML template in Baggins article generator correctly references `assets/signature.png`, and the article CSS/layout files were migrated. The signature image was not.

This affected ALL 12 papers (day-001.html through day-012.html) — it was never working in TR2.

## Discovery
Flagged during morning review (March 17, 2026). Investigation confirmed all 12 papers had the same broken image — it was never working in TR2.

## Fix Applied
Migrated `signature.png` from `trainingrun-site` repo to `TR2/assets/signature.png`.

Commit: `243adb7` — "Migrate signature.png from trainingrun-site repo"

## Verification
Image renders correctly on the live site at `trainingrun.ai/day-012.html` and `trainingrun.ai/day-011.html`. GitHub Pages deployed within 1 minute.

## Learning for Agents
When migrating a site to a new repository, ALL referenced assets must be migrated — not just code and layout files. Every `src`, `href`, or file path in HTML/CSS/JS must have the corresponding file in the new repo. Run a broken-link check after migration to catch missing assets before they reach production.

## Prevention
- Baggins should verify all referenced assets exist before publishing a new paper
- A post-publish audit step should check for broken images (HTTP 404 on asset URLs)
- Migration checklists should include an explicit "verify all assets" step

## Tags
asset-migration, broken-image, template, baggins, signature
