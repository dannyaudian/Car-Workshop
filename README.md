# Car Workshop Modules – BY Innovasi Terbaik Bangsa

This repository contains a set of integrated Frappe/ERPNext modules to manage modern automotive workshop operations. It includes detailed management of customer vehicles, job types, parts inventory, service packages, and flexible pricing via a dedicated service price list mechanism.

---

## Modules Included

### 1. Customer Vehicle

Manage vehicle records linked to customers, complete with brand/model linkage, fuel type, odometer logs, and service history.

**Features:**

* License plate validation (Indonesian format)
* Auto-fetch customer and model info
* Logs changes via `Vehicle Change Log`
* UI buttons to view last change and change list

### 2. Job Type

Define job templates for internal or outsourced services (OPL).

**Features:**

* Supports job components (`Job Type Item`)
* Calculates total job cost from items
* UI fetches latest price from `Service Price List`
* Validates structure depending on internal/OPL type

### 3. Part

Manage spare parts with compatibility mapping.

**Features:**

* Unique part number naming (`{part_number} - {part_name}`)
* Fetches `Item` rate to update `current_price`
* Barcode scanning via camera using `BarcodeDetector API`
* UI fallback prompt if scanner not supported
* Ensures compatibility (brand ↔ model) with validations

### 4. Service Package

Bundle multiple jobs and parts into fixed-price packages.

**Features:**

* Calculates total price and duration automatically
* Supports fallback job/part rate if amount not provided
* On update, syncs with ERPNext’s `Item Price`

### 5. Service Price List

Central pricing engine for `Job Type`, `Part`, and `Service Package`.

**Features:**

* Supports active/inactive status, currency, date ranges
* Prevents overlapping price entries
* Auto-deactivates conflicting prices
* Includes public API:

```python
car_workshop.car_workshop.doctype.service_price_list.get_active_service_price.get_active_service_price
```

Returns:

```json
{
  "rate": 350000,
  "tax_template": "Standard - ID"
}
```

---

## ⚙️ Installation

1. Place each component in its respective path:

   * `doctype/customer_vehicle/`
   * `doctype/job_type/`
   * `doctype/part/`
   * `doctype/service_package/`
   * `doctype/service_price_list/`

2. Run migrations:

```bash
bench migrate
```

---

## ✅ Usage Highlights

* Add and track customer vehicles
* Design and calculate service jobs (internal/OPL)
* Bundle fixed packages with smart pricing
* Scan barcode parts directly in browser
* Maintain historical and effective pricing

---

## 📌 Requirements

* Frappe Framework >= v15
* ERPNext >= v15
* Chrome 83+ / Edge Chromium / Firefox 88+ (for barcode scanning)

---

## 🔐 Best Practices

* Use `Service Price List` for all dynamic pricing
* Run periodic audits on price overlaps & vehicle logs
* Categorize parts and services clearly for reporting

---

## 📞 Support

For bugs, ideas, or deployment help, please reach out via GitHub Issues or your ERP team.

---

**Note:** Ensure regular backups and test all pricing rules before deploying to production.
