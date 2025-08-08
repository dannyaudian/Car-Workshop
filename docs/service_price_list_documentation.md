# Service Price List Documentation

## Overview

The Service Price List system provides a flexible and powerful mechanism for managing prices of various services and parts in the Car Workshop application. It allows for time-based pricing, multiple price lists, and seamless integration with the workshop operations.

## Core Functionality

The Service Price List system enables workshop managers to:

- Define prices for different service components (Job Types, Parts, Service Packages)
- Support multiple price lists for different customer segments or promotions
- Set date-based validity periods for seasonal pricing or promotions
- Automatically activate and deactivate prices based on dates
- Retrieve active prices through a standardized API

## Key Components

### Service Price List DocType

The central entity that defines a price for a specific service component in a specific price list.

#### Fields

- **Reference Type**: The type of item being priced (Job Type/Part/Service Package)
- **Reference Name**: The specific item being priced
- **Price List**: The price list this entry belongs to
- **Rate**: The price amount
- **Currency**: Currency for the price (defaults to IDR)
- **Tax Template**: Optional tax template to apply
- **Valid From**: Optional start date for this price
- **Valid Upto**: Optional end date for this price
- **Is Active**: Whether this price is currently active

#### Behavior

- **Date Validation**: Ensures valid_from is before valid_upto
- **Duplicate Prevention**: Prevents conflicting active prices for the same item
- **Reference Verification**: Checks that the referenced item actually exists
- **Auto-Deactivation**: Automatically deactivates conflicting prices when a new one is activated
- **Default Application**: Applies default currency if not specified

### Price Retrieval API

A standardized API for retrieving active prices based on reference type, name, and price list.

#### get_active_service_price

```python
get_active_service_price(reference_type, reference_name, price_list)