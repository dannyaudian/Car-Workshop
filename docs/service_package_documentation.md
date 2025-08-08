# Service Package Documentation

## Overview

The Service Package system provides a powerful way to bundle jobs and parts into pre-defined packages for common vehicle services in the Car Workshop application. It enables efficient service offering, consistent pricing, and streamlined operations.

## Core Functionality

The Service Package system enables workshop managers to:

- Create standardized packages combining labor (job types) and parts
- Automatically calculate package pricing based on component rates
- Apply package pricing across different price lists
- Track estimated time for service completion
- Efficiently apply service packages to work orders

## Key Components

### Service Package DocType

The main entity representing a bundled service offering that can include both labor (job types) and parts.

#### Fields

- **Package Name**: Unique name for the service package
- **Price List**: Optional price list this package is associated with
- **Price**: Total price of the package (auto-calculated)
- **Currency**: Currency for the price (defaults to IDR)
- **Description**: Detailed description of the service package
- **Is Active**: Whether this package is currently active
- **Details**: Child table containing the components of the package

#### Behavior

- **Auto-calculation**: Automatically calculates total price based on components
- **Price List Integration**: Updates linked price list entries when modified
- **Time Estimation**: Calculates estimated service time based on job types
- **Change Tracking**: Tracks modifications to package composition

### Service Package Detail DocType

Child table that defines the individual components (jobs and parts) that make up a service package.

#### Fields

- **Type**: Type of component (Job or Part)
- **Job Type**: Selected job type (when Type is "Job")
- **Part**: Selected part (when Type is "Part")
- **Quantity**: Number of this component needed
- **Rate**: Unit rate of the component (auto-fetched)
- **Amount**: Total amount for this component (quantity × rate)
- **Remarks**: Additional notes for this component

#### Behavior

- **Smart Field Display**: Shows only relevant fields based on Type selection
- **Auto-fetching**: Automatically fetches rates from Service Price List or defaults
- **Amount Calculation**: Automatically calculates amount based on quantity and rate
- **Validation**: Ensures proper selection of components based on Type

## Workflows and Processes

### Package Creation Workflow

1. **Create Service Package**:
   - Provide a unique package name
   - Select price list if applicable
   - Add description for the package
   - Set status as active if it should be immediately available

2. **Add Components**:
   - Add job types for labor components
   - Add parts for physical components
   - Set quantities for each component
   - Add any specific remarks

3. **Package Pricing**:
   - Rates are automatically fetched from Service Price List
   - Package total is automatically calculated
   - Package can be linked to a price list for consistent pricing

### Package Application Process

1. **Select Package in Work Order**:
   - Choose from available service packages
   - Package details are automatically populated

2. **Customize if Needed**:
   - Adjust quantities if required
   - Add or remove components based on specific vehicle needs

3. **Apply to Work Order**:
   - Package components are added to the work order
   - Pricing is applied based on the package definition

## Integration Points

The Service Package system integrates with several other components:

### Job Type Integration

- References job types as labor components
- Fetches current pricing from Service Price List
- Includes time estimates for scheduling

### Part Integration

- References parts as physical components
- Fetches current pricing from Service Price List
- Tracks quantity requirements for inventory planning

### Service Price List Integration

- Utilizes the Service Price List system for component pricing
- Updates price list entries when package is modified
- Supports multiple price lists for different customer segments

### Work Order Integration

- Packages can be directly applied to work orders
- Components are broken down into job types and parts in the work order
- Ensures consistent application of standard services

## Technical Architecture

### Pricing Logic

The Service Package implements a multi-level pricing resolution strategy:

1. **Service Price List**: First tries to get price from the Service Price List system
2. **Direct Field Lookup**: Then checks for standard rates in the component DocType
3. **Item Price Fallback**: Finally looks for prices in the standard Item Price system
4. **Calculated Rollup**: For job types with sub-items, calculates the total from all items

### Calculation Mechanisms

Several automatic calculations are performed:

1. **Price Calculation**:
   ```javascript
   // Calculate total package price
   function calculate_total(frm) {
       var total = 0;
       $.each(frm.doc.details || [], function(i, d) {
           total += flt(d.amount);
       });
       frm.set_value('price', total);
   }
   ```

2. **Amount Calculation**:
   ```javascript
   // Calculate amount for a single component
   function calculate_amount(cdt, cdn) {
       var row = locals[cdt][cdn];
       var amount = flt(row.quantity) * flt(row.rate);
       frappe.model.set_value(cdt, cdn, 'amount', amount);
   }
   ```

3. **Time Estimation**:
   ```python
   # Python code for calculating time estimates
   total_time = 0
   for detail in self.details:
       if detail.item_type == "Job" and detail.job_type:
           time_minutes = frappe.db.get_value("Job Type", detail.job_type, "time_minutes") or 0
           total_time += time_minutes * (detail.quantity or 1)