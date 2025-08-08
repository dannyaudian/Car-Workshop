# Work Order Documentation

## Overview

The Work Order module is a central component of the Car Workshop application, providing a complete system for managing vehicle service operations. It tracks service jobs, parts, expenses, and integrates with purchasing and inventory management.

## Core Features

### Work Order Management

- **Comprehensive Tracking**: Manage all aspects of vehicle service jobs
- **Integration**: Links with customers, vehicles, parts, and purchase orders
- **Financial Tracking**: Automatically calculates total costs from all service components
- **Material Management**: Facilitates material issues and parts management

## Key DocTypes

### Work Order

The primary document that records a service job for a customer's vehicle.

#### Fields

- **Customer Information**:
  - Customer: Link to Customer record
  - Customer Vehicle: Link to Customer Vehicle
  - Service Date: When service was performed
  - Service Advisor: Employee responsible for the service

- **Status**: Work order status (Draft/In Progress/Completed/Cancelled)

- **Work Details**:
  - Job Type Details: Services performed (child table)
  - Service Package Details: Predefined service packages (child table)
  - Part Details: Parts used in the service (child table)
  - External Expenses: Additional expenses (child table)

- **Financial Information**:
  - Total Amount: Calculated total of all services, parts, and expenses

- **Additional Notes**: Text field for comments or special instructions

#### Child Tables

The Work Order contains four primary child tables:

1. **Work Order Job Type**: Individual service tasks
2. **Work Order Service Package**: Predefined service bundles
3. **Work Order Part**: Parts used in the service
4. **Work Order Expense**: Additional external expenses

### Work Order Service Package

Represents predefined service packages used in work orders.

#### Fields

- **Service Package**: Link to the predefined Service Package record
- **Description**: Detailed description of the service package (auto-fetched)
- **Total Price**: Price of the service package (auto-fetched)
- **Currency**: Currency for the price (auto-fetched)
- **Notes**: Additional notes specific to this application of the service package

#### Behavior

- Auto-fetches description, price, and currency from the linked Service Package
- Read-only fields maintain consistency with the source package
- Allows additional notes for context-specific information

### Work Order Expense

Tracks external expenses related to a work order.

#### Fields

- **Expense Type**: Type of expense
- **Description**: Additional details about the expense
- **Amount**: Cost of the expense
- **Supplier**: Vendor providing the service/expense
- **Billable**: Whether the expense should be billed to the customer
- **GL Account**: General Ledger account for accounting
- **Purchase Order**: Associated purchase order if applicable

## Client-Side Logic

### Calculations and Updates

The client-side script provides robust functionality for:

1. **Real-time Calculations**:
   - Automatic part amount calculation (quantity × rate)
   - Total amount calculation from all sources (jobs, packages, parts, expenses)

2. **Field Dependencies**:
   - Purchase order requirement based on "Beli Baru" (New Purchase) source
   - Vendor requirement for OPL (Outsourced) job types

3. **Integration with Other Documents**:
   - Related purchase order viewing
   - Material issue creation

### Advanced User Interface

- **Custom Buttons**:
  - "Lihat Semua PO Terkait" (View All Related POs): Shows a dialog with all related purchase orders
  - "Material Issue": Creates a material issue document from the work order

- **Dynamic Dialogs**:
  - Purchase order viewer with filtering and navigation
  - Material issue creation wizard

### Service Package Handling

- Auto-loads service package details including description and pricing
- Updates totals whenever a service package is added, removed, or modified
- Maintains pricing consistency with source packages

## Server-Side Logic

### Validation and Business Rules

The server-side code enforces important business rules:

1. **Purchase Order Validation**:
   - Requires purchase orders for parts with "Beli Baru" source
   - Validates purchase orders before submission

2. **Vendor Validation**:
   - Requires vendor specification for OPL (outsourced) job types

3. **Submission Validation**:
   - Checks all required fields before submission
   - Ensures complete information for parts, job types, service packages, and expenses

### Service Package Integration

The `WorkOrderServicePackage` document includes validation logic that:
- Fetches missing values from the linked Service Package
- Ensures description, price, and currency are always correctly populated
- Maintains data consistency when values change in the source package

### Financial Calculations

Calculates the total amount by adding:
1. Part costs (quantity × rate)
2. Job type prices
3. Service package prices
4. External expense amounts

### Integration Points

- **Material Issue Creation**: API endpoint to generate material issues from work orders
- **Purchase Order Linking**: Associates parts and expenses with purchase orders
- **Service Package Linking**: Connects to predefined service packages for standard service offerings

## Workflows and Processes

### Work Order Lifecycle

1. **Creation**: 
   - New work order created with customer and vehicle information
   - Jobs, parts, and expenses added

2. **Processing**:
   - Status updated to "In Progress"
   - Materials issued through "Material Issue" function
   - External services managed through purchase orders

3. **Completion**:
   - All services recorded and verified
   - Status updated to "Completed"

### Service Package Application

1. **Selection**:
   - User selects from predefined service packages
   - System automatically pulls in details and pricing

2. **Customization**:
   - Notes can be added for specific application context
   - Core details remain synchronized with master record

3. **Calculation**:
   - Package price automatically factored into total amount
   - Consistent pricing maintained across work orders

### Material Management

The `make_material_issue` function provides a way to:
1. Create a Workshop Material Issue document from the work order
2. Transfer parts from inventory to the work order
3. Record costs and quantities accurately

## Best Practices

### When Creating Work Orders

1. **Complete Information**:
   - Always specify customer and vehicle details
   - Include all job types and parts required

2. **Source Tracking**:
   - Use the appropriate source for parts ("Beli Baru" for new purchases)
   - Include purchase order references when required

3. **Financial Accuracy**:
   - Verify all prices and amounts
   - Include all external expenses with proper documentation

4. **Service Packages**:
   - Use standard service packages whenever possible for consistency
   - Add notes to standard packages rather than modifying their core details

### When Processing Work Orders

1. **Status Updates**:
   - Keep status field updated as work progresses
   - Use "In Progress" while work is ongoing

2. **Material Management**:
   - Use the Material Issue function for proper inventory tracking
   - Record all parts used in the service

3. **Purchase Order Integration**:
   - View related purchase orders to track external services
   - Update purchase order references as they become available

## Integration with Other Modules

The Work Order module integrates with:

1. **Customer and Vehicle Management**:
   - Links to customer and vehicle records
   - Maintains service history for vehicles

2. **Inventory Management**:
   - Material issues for parts consumption
   - Stock tracking and valuation

3. **Purchasing**:
   - Integration with purchase orders for external services and parts
   - Supplier management for outsourced services

4. **Financial Management**:
   - GL account integration for expenses
   - Cost tracking and billing preparation

5. **Service Package Management**:
   - Standardized service offerings
   - Consistent pricing and descriptions
