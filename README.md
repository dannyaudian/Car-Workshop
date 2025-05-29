# Car Workshop Modules – By Innovasi Terbaik Bangsa

This repository contains a set of integrated Frappe/ERPNext modules to manage modern automotive workshop operations. It includes detailed management of customer vehicles, job types, parts inventory, service packages, and work orders for comprehensive workshop management.

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
           └── work_order_expense/
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
   * Calculate and finalize totals
   * Submit and link to invoices

3. **Management & Reporting**
   * Track service history by vehicle
   * Monitor outsourced work with vendors
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

---

## 📞 Support

For bugs, ideas, or deployment help, please reach out via GitHub Issues or your ERP team.

---

**Note:** Ensure regular backups and test all pricing rules before deploying to production.
```

I've reorganized the README with these improvements:

1. **Improved Categorization**:
   - Grouped related modules under logical categories (Vehicle, Service, Inventory, Pricing, Operations)
   - Used clearer section hierarchies with better headings

2. **Enhanced Visual Structure**:
   - Added emoji icons to main sections for quick visual reference
   - Improved the installation directory layout with a tree structure
   - Created dedicated tables and lists for clearer reading

3. **Workflow-Based Approach**:
   - Transformed "Usage Highlights" into a sequential workflow
   - Divided into Setup, Daily Operations, and Management phases
   - Makes it easier to understand the system's operational flow

4. **Better Best Practices Organization**:
   - Grouped best practices by category for easier reference
   - Added specific guidance for each major system component

This reorganized structure provides a more professional, visually appealing, and easier-to-navigate documentation that highlights all system components while maintaining a logical flow.