# Car Workshop Module Documentation

## Overview

The Car Workshop module provides a comprehensive solution for managing vehicle service operations. It includes functionality for tracking customer vehicles, service history, and maintaining detailed vehicle information. The module includes change tracking to maintain a full audit trail of all vehicle modifications.

## Key DocTypes

### Customer Vehicle

The central DocType that represents a customer's vehicle in the workshop system.

#### Fields

- **License Plate Number**: Unique identifier for the vehicle (also used for document naming)
- **VIN**: Vehicle Identification Number
- **Brand**: Link to Vehicle Brand
- **Model**: Link to Vehicle Model
- **Fuel Type**: Automatically fetched from Vehicle Model
- **Year**: Manufacturing year
- **Customer**: Link to Customer
- **Customer Name**: Fetched from Customer
- **Customer Phone**: Fetched from Customer
- **Last Odometer Reading**: Updated automatically from service history
- **Last Service Date**: Updated automatically from service history
- **Service History**: Child table for tracking service records

#### Validations

- **Plate Number**: Validates against Indonesian license plate format
- **Fuel Type**: Automatically updated based on the selected model

#### Automation

- **Service Info Update**: Updates last service date and odometer reading from completed service records
- **Change Logging**: Automatically logs all changes to key fields

### Vehicle Brand

Represents vehicle manufacturers.

#### Fields

- **Brand Name**: Unique name of the manufacturer
- **Country**: Country of origin
- **Active**: Flag to indicate if the brand is active

### Vehicle Model

Represents specific vehicle models associated with brands.

#### Fields

- **Model**: Unique model name
- **Brand**: Link to Vehicle Brand
- **Fuel Type**: Link to Fuel Type
- **Production Year Start**: Beginning year of production
- **Production Year End**: End year of production

### Vehicle Change Log

Tracks all changes made to Customer Vehicles for audit purposes.

#### Fields

- **Customer Vehicle**: Link to the vehicle being modified
- **Change Date**: When the change occurred
- **Field Name**: Name of the field that was changed
- **Old Value**: Previous value
- **New Value**: Updated value
- **Change Type**: Category of change (e.g., "Plate Change", "Owner Change")
- **DocType Reference**: Reference to the DocType where the change occurred
- **Reference Document**: Dynamic link to the referenced document
- **Updated By**: User who made the change
- **Remarks**: Additional notes about the change

#### Features

- **Immutability**: Change logs cannot be edited or deleted after creation
- **Automatic Classification**: Change types are automatically determined based on the field name
- **Notification System**: Framework for notifying stakeholders about changes

## Client-Side Scripts

### Customer Vehicle

The client-side script for Customer Vehicle provides:

1. **Brand-Model Filtering**: When a brand is selected, the model field is filtered to show only models for that brand
2. **Change History Actions**:
   - **View Latest Change**: Shows a dialog with details of the most recent change
   - **View All Changes**: Navigates to a filtered list of all changes for the vehicle

## Server-Side Logic

### Vehicle Data Validation

- **License Plate Validation**: Uses regex to validate Indonesian license plate formats
- **Automatic Updates**: Ensures fuel type is kept in sync with the selected model

### Change Tracking

A comprehensive change tracking system that:

1. **Logs Creation**: Records when a vehicle is first added to the system
2. **Tracks Field Changes**: Monitors changes to key fields (plate number, VIN, brand, model, year, customer)
3. **Maintains History**: Creates immutable log entries for all changes

### Service History Management

- **Latest Service Data**: Automatically updates vehicle with the most recent service information
- **Odometer Tracking**: Maintains the last known odometer reading

## API Integration

The module includes API endpoints for:

1. **Latest Vehicle Log**: Retrieves the most recent change for a specific vehicle
   - Endpoint: `car_workshop.car_workshop.api.get_latest_vehicle_log`
   - Args: `customer_vehicle`

## User Interfaces

### Vehicle Change Viewing

Users can:
1. See the latest change in a formatted dialog showing:
   - Field changed
   - Old and new values
   - Date and time of change
   - User who made the change
   - Any additional remarks

2. View a complete history of all changes by navigating to the Vehicle Change Log list with a pre-filtered view

## Permissions

### Role-Based Access

1. **System Manager**: Full access to all features
2. **Workshop Manager**: Can create and edit records, but cannot delete certain types
3. **Technician**: Read-only access to vehicle information

## Data Protection

- **Change Logs**: Protected from modification to maintain audit integrity
- **Validation**: Ensures data consistency and prevents invalid entries

## Integration Points

The module is designed to integrate with:

1. **ERPNext Customer**: Links vehicles to standard ERPNext customer records
2. **Custom Service Modules**: Can be extended to connect with service scheduling and billing

## Development Guidelines

When extending this module:

1. **Change Tracking**: Always update the `log_vehicle_updates` function when adding new tracked fields
2. **Validation**: Add new validations to the `validate` method in the CustomerVehicle class
3. **UI Customization**: Extend the client-side JS to add new actions or filters