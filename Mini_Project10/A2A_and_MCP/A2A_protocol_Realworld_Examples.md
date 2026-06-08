# A2A Protocol Real-World Examples

This document explains how an A2A client and A2A server can work in real product scenarios. The examples are conceptual and map common application workflows to A2A-style agent-to-agent communication.

## Core A2A Pattern

```mermaid
flowchart LR
    User["User / App UI"]
    Client["A2A Client Agent\ninside app/backend"]
    Discovery["Agent Card Discovery\n/.well-known/agent-card.json"]
    Protocol["A2A Protocol\nJSON-RPC / streaming"]
    Server["Remote A2A Server Agent"]
    Tools["Tools / APIs / Databases"]
    Response["Streamed response/status"]

    User --> Client
    Client --> Discovery
    Discovery --> Server
    Client --> Protocol
    Protocol --> Server
    Server --> Tools
    Tools --> Server
    Server --> Response
    Response --> Client
    Client --> User
```

## 1. Swiggy / Zomato Food Ordering

### Use Case

A customer asks the app to find food, apply offers, place an order, and track delivery.

Example user input:

```text
Order chicken biryani near Indiranagar under Rs. 400 and deliver it quickly.
```

### Wiring Diagram

```mermaid
flowchart LR
    App["Swiggy/Zomato App\nA2A Client"]
    Discovery["Discover Food Ordering Agent Card"]
    Ordering["Food Ordering A2A Server Agent"]
    Restaurant["Restaurant Search Agent"]
    Menu["Menu Availability Agent"]
    Offers["Offers/Pricing Agent"]
    Delivery["Delivery ETA Agent"]
    Payment["Payment Agent"]
    Tracking["Order Tracking Agent"]

    App --> Discovery
    Discovery --> Ordering
    App -->|"A2A JSON-RPC request"| Ordering
    Ordering --> Restaurant
    Ordering --> Menu
    Ordering --> Offers
    Ordering --> Delivery
    Ordering --> Payment
    Ordering --> Tracking
    Ordering -->|"stream status"| App
```

### Steps

1. App sends user request to the remote food ordering A2A server.
2. Server checks restaurants near the user.
3. Menu agent confirms item availability.
4. Offers agent applies coupons and calculates price.
5. Delivery agent estimates delivery time.
6. Payment agent validates UPI/card/wallet.
7. Order tracking agent streams live updates.

### Streamed Output Example

```text
Finding restaurants near Indiranagar...
Found biryani at 4 restaurants.
Applying best coupon...
Final price: Rs. 372.
Assigning delivery partner...
Order confirmed. ETA 31 minutes.
```

## 2. Uber / Ola Cab Booking

### Use Case

A customer asks the app to book a ride from pickup to destination.

Example user input:

```text
Book a cab from HSR Layout to Bangalore Airport for 2 passengers.
```

### Wiring Diagram

```mermaid
flowchart LR
    App["Uber/Ola App\nA2A Client"]
    Discovery["Discover Ride Booking Agent Card"]
    RideServer["Ride Booking A2A Server Agent"]
    Location["Location Validation Agent"]
    Matching["Driver Matching Agent"]
    Pricing["Fare/Pricing Agent"]
    ETA["ETA Agent"]
    Payment["Payment Agent"]
    Notify["Notification Agent"]

    App --> Discovery
    Discovery --> RideServer
    App -->|"A2A streaming request"| RideServer
    RideServer --> Location
    RideServer --> Matching
    RideServer --> Pricing
    RideServer --> ETA
    RideServer --> Payment
    RideServer --> Notify
    RideServer -->|"stream booking updates"| App
```

### Steps

1. App sends pickup, drop, passenger count, and ride preference.
2. Location agent validates pickup/drop coordinates.
3. Pricing agent calculates estimated fare.
4. ETA agent estimates pickup and trip duration.
5. Driver matching agent finds nearby drivers.
6. Payment agent performs pre-check.
7. Notification agent sends ride confirmation.

### Streamed Output Example

```text
Validating pickup location...
Estimating fare...
Estimated fare: Rs. 1,250.
Searching nearby drivers...
Driver Ravi accepted. Pickup ETA: 4 minutes.
Ride confirmed.
```

## 3. HDFC Bank / Banking Assistant

### Use Case

A customer asks a banking app for loan eligibility, card support, fraud help, or transaction assistance.

Example user input:

```text
Check if I am eligible for a personal loan of Rs. 5 lakhs and explain the EMI options.
```

### Wiring Diagram

```mermaid
flowchart LR
    Mobile["HDFC Mobile App\nA2A Client"]
    Discovery["Discover Banking Specialist Agent Card"]
    BankServer["Banking A2A Server Agent"]
    Auth["Customer Auth/KYC Agent"]
    Eligibility["Loan Eligibility Agent"]
    Risk["Risk/Policy Agent"]
    EMI["EMI Calculator Agent"]
    Compliance["Compliance Agent"]
    CRM["CRM/Core Banking APIs"]

    Mobile --> Discovery
    Discovery --> BankServer
    Mobile -->|"A2A secure request"| BankServer
    BankServer --> Auth
    BankServer --> Eligibility
    BankServer --> Risk
    BankServer --> EMI
    BankServer --> Compliance
    BankServer --> CRM
    BankServer -->|"stream decision + explanation"| Mobile
```

### Steps

1. Mobile app authenticates the user and sends the request.
2. Banking A2A server receives the request.
3. Auth/KYC agent confirms customer identity and consent.
4. Eligibility agent checks income, account history, and credit rules.
5. Risk/policy agent applies bank policy.
6. EMI agent calculates possible repayment plans.
7. Compliance agent ensures the response follows regulatory language.

### Streamed Output Example

```text
Verifying customer profile...
Checking eligibility...
Calculating EMI options...
You may be eligible for Rs. 5 lakhs subject to final verification.
Example EMI for 36 months: Rs. XX,XXX.
Please review terms before applying.
```

## 4. Zepto / Quick Commerce Delivery

### Use Case

A customer asks for groceries or essentials with fast delivery.

Example user input:

```text
Send milk, bread, eggs, and bananas to my home in 10 minutes if available.
```

### Wiring Diagram

```mermaid
flowchart LR
    App["Zepto App\nA2A Client"]
    Discovery["Discover Quick Commerce Agent Card"]
    CommerceServer["Quick Commerce A2A Server Agent"]
    Catalog["Catalog Agent"]
    Inventory["Dark Store Inventory Agent"]
    Substitution["Substitution Agent"]
    Pricing["Pricing/Offers Agent"]
    Picker["Picker Assignment Agent"]
    Delivery["Rider/Delivery Agent"]
    Payment["Payment Agent"]

    App --> Discovery
    Discovery --> CommerceServer
    App -->|"A2A streaming order request"| CommerceServer
    CommerceServer --> Catalog
    CommerceServer --> Inventory
    CommerceServer --> Substitution
    CommerceServer --> Pricing
    CommerceServer --> Picker
    CommerceServer --> Delivery
    CommerceServer --> Payment
    CommerceServer -->|"stream order status"| App
```

### Steps

1. App sends basket and delivery location.
2. Catalog agent normalizes item names.
3. Inventory agent checks the nearest dark store.
4. Substitution agent suggests replacements for unavailable items.
5. Pricing agent applies discounts and computes total.
6. Picker agent assigns a store picker.
7. Delivery agent assigns a rider.
8. Payment agent confirms payment.

### Streamed Output Example

```text
Checking nearest dark store...
Milk, bread, eggs, and bananas are available.
Applying offers...
Assigning picker...
Rider assigned. Delivery ETA: 9 minutes.
Order confirmed.
```

## How This Maps to Your Current A2A Demo

Your current notebooks follow the same pattern:

```mermaid
flowchart LR
    Client["a2a_client.ipynb\nA2A Client"]
    Discovery["Agent Card Discovery"]
    Server["a2a_server.ipynb\nA2A Server"]
    Foundry["Azure AI Foundry Agent\nA2A-MCP-Agent"]
    MCP["Microsoft Learn MCP"]

    Client --> Discovery
    Discovery --> Server
    Client -->|"A2A JSON-RPC streaming"| Server
    Server --> Foundry
    Foundry --> MCP
    Foundry --> Server
    Server -->|"TaskArtifactUpdateEvent stream"| Client
```

In production, replace the demo Foundry/MCP backend with domain-specific systems:

| Demo component | Real-world equivalent |
| --- | --- |
| `a2a_client.ipynb` | Mobile app, web app, call center app, Teams bot |
| `a2a_server.ipynb` | Remote business capability agent |
| `A2A-MCP-Agent` | Domain specialist agent |
| Microsoft Learn MCP | Restaurant APIs, bank APIs, logistics APIs, inventory APIs |
| Streaming output | Live order, booking, eligibility, or delivery updates |

## Why A2A Helps

- The client does not need to know every backend service.
- Each remote agent publishes its capabilities through an Agent Card.
- Teams can own independent agents: payments, delivery, pricing, risk, inventory.
- Streaming responses provide real-time progress updates.
- The same protocol pattern works across food, mobility, banking, and logistics.

