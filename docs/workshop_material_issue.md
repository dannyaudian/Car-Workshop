# Workshop Material Issue Documentation

## Overview

The Workshop Material Issue module allows workshop staff to record materials (parts and items) being issued from inventory to work orders. This module integrates with ERPNext's inventory management system to track the movement of materials and ensure proper accounting for used parts.

## Key Features

- Issue parts and materials to specific work orders
- Track consumed quantities against required quantities
- Validate stock availability before issuing
- Automatic creation of stock entries (Material Issue)
- Integration with Work Orders to update consumed quantities
- Support for batch and serial number tracking

## Document Structure

### Workshop Material Issue

The main document that records the movement of materials from warehouse to a work order.

**Key Fields:**
- **Series**: Auto-generated document number
- **Work Order**: The work order that will receive the materials
- **Posting Date**: When the transaction occurred
- **Source Warehouse**: Warehouse from which materials are issued
- **Issued By**: Employee who performed the material issue
- **Status**: Current status of the document (Draft, Submitted, Cancelled)
- **Items**: List of parts/materials being issued

### Workshop Material Issue Item

The child table that contains details of each individual item being issued.

**Key Fields:**
- **Part**: Reference to the Part master
- **Item Code**: The inventory item code (auto-fetched from Part)
- **Description**: Description of the part
- **Qty**: Quantity being issued
- **UOM**: Unit of Measurement
- **Rate**: Valuation rate of the item
- **Amount**: Total value (Qty × Rate)
- **Batch No**: (Optional) For batch-tracked items
- **Serial No**: (Optional) For serial number tracked items

## Workflow

### Creating a New Material Issue

1. Navigate to **Car Workshop → Workshop Material Issue → New**
2. Select the Work Order for which materials will be issued
3. Select the Source Warehouse
4. Add parts to the items table by:
   - Using the "Fetch Parts from Work Order" button
   - Manually adding parts one by one
5. Verify the quantities to be issued
6. Save and Submit the document

### Fetching Parts from Work Order

The "Fetch Parts from Work Order" button automatically:
- Retrieves all parts required for the selected work order
- Shows current stock availability in the selected warehouse
- Calculates remaining quantities that need to be issued
- Fills in valuation rates from inventory

### Stock Validation

Before submission, the system checks:
- If all items exist in inventory
- If sufficient stock is available in the selected warehouse
- If batch/serial numbers are valid (if applicable)

### Submission Process

When a Workshop Material Issue is submitted:
1. A Stock Entry of type "Material Issue" is created automatically
2. The consumed quantity in the Work Order is updated
3. The inventory is reduced accordingly
4. The document status changes to "Submitted"

### Cancellation Process

When a Workshop Material Issue is cancelled:
1. The linked Stock Entry is cancelled
2. The consumed quantity in the Work Order is reduced
3. The inventory is restored
4. The document status changes to "Cancelled"

## Integration Points

### Work Order Integration

- Material Issue documents are linked to Work Orders
- Consumed quantities in Work Orders are updated automatically
- Work Order status can change based on material consumption

### Inventory Integration

- Creates Stock Entry documents to track inventory movement
- Updates actual stock quantities in the Bin
- Considers valuation rates for accounting

## User Permissions

The following roles have access to Workshop Material Issue:
- **Workshop Manager**: Full access (create, submit, amend, cancel)
- **Stock Manager**: Full access except deletion
- **Technician**: Read-only access

## Reports and Dashboards

Workshop Material Issue data feeds into several reports:
- Work Order Material Consumption Report
- Inventory Movement Analysis
- Part Usage Analysis

## Best Practices

1. **Always verify stock availability** before issuing materials to prevent negative stock
2. **Use the Fetch function** to ensure you're issuing the correct parts for the work order
3. **Check valuation rates** to ensure proper costing of the work order
4. **Verify warehouse selection** to ensure materials are issued from the correct location
5. **Submit material issues promptly** to keep work order status and inventory accurate

## Troubleshooting

### Common Issues

1. **Insufficient Stock Error**
   - Verify actual stock in the warehouse
   - Check if stock is reserved by other documents
   - Consider transferring stock from another warehouse

2. **Work Order Not Updating**
   - Ensure the Work Order is in a valid state (not Completed or Cancelled)
   - Check if the correct Part is linked to the Work Order's required items

3. **Valuation Rate Missing**
   - Ensure the item has been properly received with a valuation rate
   - Check the Item master for default valuation rate

## API Reference

For developers, the module provides several API methods:

### `get_work_order_parts(work_order)`
Retrieves all parts required for a work order with stock information.

### Custom Buttons in Work Order
The module adds a "Material Issue" button to the Work Order form to quickly create material issues.