# API Manager Overview

The `APIManager` is a centralized class that handles all interactions with the external API. It is responsible for fetching, creating, updating, and deleting data related to products, categories, and prices. Below is a detailed overview of the API calls made, their purposes, and the endpoints used.

---

## **1. API Calls Overview**

### **1.1 GET Requests**

#### **Categories Cache**
- **Purpose**: Fetch all product categories for caching and further processing.
- **Endpoint**: `GET /admin/WebAPI/v2/categories`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `accept: text/plain`
- **Parameters**:
  - `limit`: Maximum number of categories per request (default: 100).
  - `offset`: Pagination offset.
- **Response**:
  - `id`: Category ID.
  - `number`: Category number.
  - `texts`: Category names and descriptions.
  - `parentIds`: Parent category IDs.

#### **Products Cache**
- **Purpose**: Fetch all products for caching and further processing.
- **Endpoint**: `GET /admin/WebAPI/v2/products`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `accept: text/plain`
- **Parameters**:
  - `limit`: Maximum number of products per request (default: 100).
  - `offset`: Pagination offset.
  - `include`: Comma-separated list of additional data to include (e.g., `settings`, `prices`, `categories`).
- **Response**:
  - `id`: Product ID.
  - `number`: Product number.
  - `settings`: Product settings (e.g., descriptions, metadata).
  - `prices`: Product prices.
  - `categories`: Associated categories.

#### **Tilbudspriser (Special Offer Prices)**
- **Purpose**: Fetch products with their categories, prices, and settings for managing special offer prices.
- **Endpoint**: `GET /admin/WebAPI/v2/products`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `accept: text/plain`
- **Parameters**:
  - `limit`: Maximum number of products per request (default: 100).
  - `offset`: Pagination offset.
  - `include`: `settings,prices,categories`.
- **Response**:
  - `id`: Product ID.
  - `number`: Product number.
  - `settings`: Product settings (e.g., `customField3`).
  - `prices`: Product prices.
  - `categories`: Associated categories.

---

### **1.2 POST Requests**

#### **Create New Products**
- **Purpose**: Create new products in the system.
- **Endpoint**: `POST /admin/WebAPI/v2/products`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "number": "<product_number>",
    "name": "<product_name>",
    "vendorNumber": "<vendor_number>",
    "costPrice": <cost_price>,
    "stockCount": <stock_count>
  }
  ```
- **Response**:
  - `id`: Created product ID.

#### **Create Product Settings**
- **Purpose**: Add settings (e.g., descriptions, metadata) to a product.
- **Endpoint**: `POST /admin/WebAPI/v2/products/<product_id>/settings`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "items": [
      {
        "languageId": <language_id>,
        "name": "<product_name>",
        "shortDescription": "<short_description>",
        "longDescription": "<long_description>"
      }
    ]
  }
  ```
- **Response**:
  - `id`: Created settings ID.

#### **Create Product Prices**
- **Purpose**: Add prices to a product.
- **Endpoint**: `POST /admin/WebAPI/v2/products/<product_id>/prices`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "items": [
      {
        "quantity": 1,
        "unitPrice": <unit_price>,
        "specialOfferPrice": <special_offer_price>,
        "currencyCode": "DKK"
      }
    ]
  }
  ```
- **Response**:
  - `id`: Created price ID.

---

### **1.3 PATCH Requests**

#### **Update Product Settings**
- **Purpose**: Update specific settings for a product.
- **Endpoint**: `PATCH /admin/WebAPI/v2/products/<product_id>/settings`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "items": [
      {
        "languageId": <language_id>,
        "customField3": "<custom_field3_value>"
      }
    ]
  }
  ```
- **Response**:
  - `id`: Updated settings ID.

#### **Update Product Prices**
- **Purpose**: Update prices for a product.
- **Endpoint**: `PATCH /admin/WebAPI/v2/products/<product_id>/prices`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "items": [
      {
        "quantity": 1,
        "unitPrice": <new_unit_price>,
        "specialOfferPrice": <new_special_offer_price>
      }
    ]
  }
  ```
- **Response**:
  - `id`: Updated price ID.

---

### **1.4 DELETE Requests**

#### **Delete Product Prices**
- **Purpose**: Remove specific prices from a product.
- **Endpoint**: `DELETE /admin/WebAPI/v2/products/<product_id>/prices`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "items": [
      {
        "quantity": 1,
        "currencyCode": "DKK"
      }
    ]
  }
  ```
- **Response**:
  - `id`: Deleted price ID.

---

## **2. Missing API Calls**

### **2.1 Fetch Single Product**
- **Purpose**: Retrieve detailed information about a single product.
- **Endpoint**: `GET /admin/WebAPI/v2/products/<product_id>`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `accept: text/plain`
- **Use Case**: Useful for debugging or fetching specific product details.

### **2.2 Fetch Single Category**
- **Purpose**: Retrieve detailed information about a single category.
- **Endpoint**: `GET /admin/WebAPI/v2/categories/<category_id>`
- **Headers**:
  - `Authorization: Basic <Base64-encoded API key>`
  - `accept: text/plain`
- **Use Case**: Useful for debugging or fetching specific category details.

---

## **3. Summary**

The `APIManager` provides a centralized interface for interacting with the external API. It supports:
- Fetching and caching categories and products.
- Creating new products, settings, and prices.
- Updating and deleting product settings and prices.

### **Next Steps**
1. Implement missing API calls for fetching single products and categories.
2. Ensure all API calls are thoroughly tested.
3. Document any additional use cases or edge cases as they arise.