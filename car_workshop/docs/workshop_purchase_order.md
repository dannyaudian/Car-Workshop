# Workshop Purchase Order Documentation

## Overview

The Workshop Purchase Order module allows workshop staff to create and manage purchase orders for parts, outside processing labor (OPL), and expenses related to work orders. This module integrates with the Workshop's inventory management and supplier management systems to streamline procurement processes.

## Key Features

- Create purchase orders for parts, OPL services, and miscellaneous expenses
- Link purchase orders to specific work orders
- Track billable vs non-billable items
- Manage different order sources (Stock, New Purchase, Consignment)
- Support tax calculations at line item level
- Generate purchase receipts for received parts
- Create purchase invoices for payment processing

## Document Structure

### Workshop Purchase Order

The main document that records the procurement of parts and services for workshop operations.

**Key Fields:**
- **Purchase Order ID**: Unique identifier for the purchase order
- **Supplier**: The vendor supplying the parts or services
- **Purchase Type**: Type of purchase (Part, OPL, Expense, Inventory Replenishment)
- **Work Order**: Optional link to related work order
- **Transaction Date**: When the order was placed
- **Expected Delivery**: Expected delivery date
- **Order Source**: Source of the order (Dari Stok, Titipan, Beli Baru)
- **Status**: Current status (Draft, Submitted, Received, Cancelled)
- **Default Tax Template**: Tax template to apply to items
- **Items**: List of items being purchased

### Workshop Purchase Order Item

The child table that contains details of each individual item being ordered.

**Key Fields:**
- **Item Type**: Type of item (Part, OPL, Expense)
- **Reference**: Link to the reference document (Part, Job Type, Expense Type)
- **Description**: Description of the item
- **Quantity**: Quantity being ordered
- **UOM**: Unit of Measurement
- **Rate**: Purchase rate
- **Amount**: Total value (Quantity × Rate)
- **Tax Template**: Specific tax template for this item
- **Billable**: Whether this item is billable to the customer

## Workflow

### Creating a New Purchase Order

1. Navigate to **Car Workshop → Workshop Purchase Order → New**
2. Enter a unique Purchase Order ID
3. Select the Supplier and Purchase Type
4. Optionally link to a Work Order
5. Set Transaction Date and Expected Delivery Date
6. Select Order Source
7. Add items using one of the following methods:
   - "Fetch Items from Work Order" button
   - "Add Item Manually" button
8. Set tax templates if applicable
9. Save and Submit the document

### Fetching Items from Work Order

The "Fetch Items from Work Order" button provides these options:
- Fetch Parts, OPL Jobs, and/or Expenses
- Filter for items without existing POs
- Mark items as billable or non-billable
- Apply text filters to find specific items

### Adding Items Manually

The "Add Item Manually" dialog allows you to:
- Select the item type (Part, OPL, Expense)
- Choose the specific reference item
- Set quantity, rate, and UOM
- Configure tax settings
- Mark as billable or non-billable

### Tax Calculation

The purchase order supports:
- Default tax templates at the document level
- Item-specific tax templates
- Option to apply default tax to all items
- Tax summary calculation

### Submission Process

When a Workshop Purchase Order is submitted:
1. Order status changes to "Submitted"
2. The Work Order is updated with PO references
3. The document can no longer be edited directly
4. Purchase Receipts and Invoices can now be created

### Receiving Process

When items are received:
1. Click "Mark as Received" or generate a Purchase Receipt
2. Order status changes to "Received"
3. For parts, inventory is updated via Stock Entry

## Related Documents

### Workshop Purchase Receipt

Records the receipt of parts ordered via Purchase Order.

**Key Functions:**
- Tracks received quantities against ordered quantities
- Records receipt date and warehouse
- Creates Stock Entries for parts to update inventory
- Updates Purchase Order status

### Workshop Purchase Invoice

Records supplier invoices for payment processing.

**Key Functions:**
- Links to Purchase Orders
- Supports multiple item types (Part, OPL, Expense)
- Tracks billable vs non-billable amounts
- Integrates with payment system
- Supports document attachments

## Integration Points

### Work Order Integration

- Purchase Orders can be created directly from Work Orders
- Work Order parts and services are updated with PO references
- Work Order costing reflects purchase prices

### Inventory Integration

- Purchase Receipts create Stock Entries
- Parts are received into specified warehouses
- Valuation rates are updated based on purchase prices

### Financial Integration

- Purchase Invoices can be created from Purchase Orders
- Payment Entries link to Purchase Invoices
- Tax calculations flow to accounting

## User Permissions

The following roles have access to Workshop Purchase Order:
- **System Manager**: Full access
- **Purchase User**: Create, submit, amend, cancel (no deletion)

## Dashboard and Reports

The Purchase Order dashboard shows:
- Total Amount
- Billable Amount
- Non-Billable Amount

Related documents are accessible via the dashboard:
- Purchase Receipts
- Purchase Invoices
- Stock Entries

## Best Practices

1. **Link to Work Orders** whenever possible for better tracking
2. **Use the Fetch function** to ensure correct parts and services
3. **Verify tax settings** before submission
4. **Mark billable items correctly** for customer invoicing
5. **Create Purchase Receipts promptly** when items are received
6. **Verify supplier details** before creating Purchase Invoices

## Workflow States

Purchase Orders progress through these states:
1. **Draft**: Initial state, editable
2. **Submitted**: Order confirmed with supplier
3. **Received**: All items have been received
4. **Cancelled**: Order has been cancelled

## Troubleshooting

### Common Issues

1. **Cannot Create Purchase Receipt**
   - Verify Purchase Order is submitted
   - Check if all items are already received

2. **Tax Calculation Issues**
   - Check if tax templates are correctly configured
   - Verify if default tax is applied correctly

3. **Work Order Updates Missing**
   - Ensure Work Order is in a valid state
   - Check if the correct reference items are linked

## API Reference

For developers, the module provides several API methods:

### `make_purchase_receipt(source_name)`
Creates a Purchase Receipt from a Purchase Order.

### `check_duplicate_po(work_order, item_type, reference_doctype, current_po)`
Checks if a duplicate Purchase Order exists for the same items.

### `fetch_work_order_items(work_order, fetch_parts, fetch_opl, fetch_expenses, only_without_po, filter_text, current_po)`
Retrieves items from a Work Order based on filter criteria.

### `generate_receipt(purchase_order)`
Generates a Purchase Receipt from a submitted Purchase Order.