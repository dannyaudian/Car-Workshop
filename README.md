# Car Workshop Modules – By Innovasi Terbaik Bangsa

This repository contains a set of integrated Frappe/ERPNext modules to manage modern automotive workshop operations. It includes detailed management of customer vehicles, job types, parts inventory, service packages, work orders, purchase orders, and invoicing for comprehensive workshop management.

---

## 📋 Modules Included

### Vehicle Management

#### 1. Customer Vehicle

Manage vehicle records linked to customers, complete with brand/model linkage, fuel type, odometer logs, and service history.

**Features:**
* License plate validation (Indonesian format)
* Auto-fetch customer and model info
* Logs changes via `Vehicle Change Log`
* UI buttons to view last change and change list

### Service Management

#### 2. Job Type

Define job templates for internal or outsourced services (OPL).

**Features:**
* Supports job components (`Job Type Item`)
* Calculates total job cost from items
* UI fetches latest price from `Service Price List`
* Validates structure depending on internal/OPL type

#### 3. Service Package

Bundle multiple jobs and parts into fixed-price packages.

**Features:**
* Calculates total price and duration automatically
* Supports fallback job/part rate if amount not provided
* On update, syncs with ERPNext's `Item Price`

### Inventory Management

#### 4. Part

Manage spare parts with compatibility mapping.

**Features:**
* Unique part number naming (`{part_number} - {part_name}`)
* Fetches `Item` rate to update `current_price`
* Barcode scanning via camera using `BarcodeDetector API`
* UI fallback prompt if scanner not supported
* Ensures compatibility (brand ↔ model) with validations

### Pricing System

#### 5. Service Price List

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

### Workshop Operations

#### 6. Work Order

Comprehensive service records management for vehicle repair and maintenance operations.

**Features:**
* Auto-naming with format `WO-.YYYY.-.####`
* Links to customer, vehicle, service date, and advisor
* Configurable source (Beli Baru, Part Bekas, etc.)
* Automatic total amount calculation
* Built-in validation rules for submission

**Child Tables:**
* **Work Order Job Type** - Service jobs with OPL vendor support
* **Work Order Service Package** - Predefined service bundles
* **Work Order Part** - Parts used with quantity, rate, and amount
* **Work Order Expense** - Additional costs with supplier tracking

**Integration Points:**
* Connects with Purchase Orders for vendor outsourcing
* Links to Sales Invoices for billing
* Supports dashboard views of related documents
* Integrates with calendar views for scheduling

**JavaScript Features:**
* Dynamic field validation based on source
* Automatic price calculations across all child tables
* Real-time total updates when quantities or rates change
* Vendor and PO management for outsourced jobs
* Dialog view for related purchase orders

#### 7. Workshop Purchase Order

Manage purchase orders for parts and outsourced labor services (OPL).

**Features:**
* Links to work orders and suppliers
* Supports multiple item types (Part, OPL)
* Tracks status through the procurement process
* Validates items against required specifications

#### 8. Workshop Purchase Invoice

Process supplier invoices for parts and outsourced services with payment tracking.

**Features:**
* Auto-naming with format `WPI-.YYYY.-`
* Links to suppliers, work orders, and purchase orders
* Handles different item types (Part, OPL, Expense)
* Calculates totals with tax handling
* Integrated with Payment Entry for payment processing
* Validates items to prevent duplicate payments

**Integration Points:**
* Connected to Payment Entry for payment processing
* Links to Work Orders and Purchase Orders
* Tracks payment status (Draft, Submitted, Paid, Cancelled)

**JavaScript Features:**
* One-click Payment Entry creation
* Dynamic field validation based on item type
* Real-time total calculations
* Auto-fill from Purchase Order references
* Visibility controls based on item types

---

## ⚙️ Installation

1. Place each component in its respective path:

   ```
   car_workshop/
   └── car_workshop/
       └── doctype/
           ├── customer_vehicle/
           ├── job_type/
           ├── part/
           ├── service_package/
           ├── service_price_list/
           ├── work_order/
           ├── work_order_job_type/
           ├── work_order_service_package/
           ├── work_order_part/
           ├── work_order_expense/
           ├── workshop_purchase_order/
           ├── workshop_purchase_invoice/
           └── workshop_purchase_invoice_item/
   ```

2. Run migrations:

   ```bash
   bench migrate
   ```

---

## ✅ Usage Workflow

1. **Setup Phase**
   * Configure job types and labor rates
   * Add parts inventory with compatibility data
   * Create service packages for common procedures
   * Set up pricing lists for all services and parts

2. **Daily Operations**
   * Register customer vehicles
   * Create work orders for service requests
   * Select appropriate job types or packages
   * Add required parts with quantities
   * Generate purchase orders for parts and outsourced labor
   * Process supplier invoices and make payments
   * Calculate and finalize totals
   * Submit and link to invoices

3. **Management & Reporting**
   * Track service history by vehicle
   * Monitor outsourced work with vendors
   * Manage supplier payments and invoices
   * Analyze service profitability
   * Review part usage patterns
   * Manage customer service timelines

---

## 📌 Requirements

* Frappe Framework >= v15
* ERPNext >= v15
* Chrome 83+ / Edge Chromium / Firefox 88+ (for barcode scanning)

---

## 🔐 Best Practices

### Data Management
* Use consistent naming conventions
* Categorize parts and services clearly for reporting
* Run periodic audits on vehicle logs

### Pricing
* Use `Service Price List` for all dynamic pricing
* Regularly review and update job types and pricing
* Check for price overlaps in scheduled services

### Work Orders
* Link each Work Order to a specific customer vehicle
* Ensure OPL jobs have vendors specified
* Use service packages for common maintenance procedures
* Validate all details before submission

### Purchase and Payment
* Create purchase orders promptly for all outsourced work
* Process supplier invoices timely for accurate accounting
* Match invoice items to purchase order references
* Use the integrated payment system for tracking payments
* Regularly reconcile outstanding payments

---

## 📞 Support

For bugs, ideas, or deployment help, please reach out via GitHub Issues or your ERP team.

---

**Note:** Ensure regular backups and test all pricing rules before deploying to production.