## **Data Controller — Architecture & Implementation Prompt**

**Context:**  
I am building a modular trading framework using ECS‑like architecture, DOD principles, and functional pipelines. The
Data Controller is a core subsystem responsible for ingestion, normalization, and unified delivery of market data from
multiple providers.

**Task:**  
Design and specify the complete plan and implementation approach for the **Data Controller** subsystem.

**Requirements:**

### **1. Architecture**

- Define the subsystem boundaries and responsibilities.
- Specify functional pipelines for:
    - WebSocket streaming
    - REST historical fetch
    - Normalization and type‑safe parsing
    - Integrity checks (sequence, timestamps, gaps)

### **2. Data Shapes & Schemas**

- Provide normalized, strongly typed data structures for:
    - Trades
    - Order book snapshots
    - Order book deltas
    - Candles
    - Ticks (unified)
- Include versioning and extensibility guidelines.

### **3. Provider Abstraction Layer**

- Define provider interface contracts:
    - `connect()`, `disconnect()`
    - `subscribe()`, `unsubscribe()`
    - `fetch_historical()`
    - `parse_*()` functions
- Show how to enforce consistent output across heterogeneous APIs.

### **4. Error Handling & Reliability**

- Reconnection strategies
- Rate‑limit backoff
- Data integrity validation
- Logging and metrics
- Health checks and provider status tracking

### **5. Modes of Operation**

- **Live streaming mode**
- **Historical batch mode**
- **Replay mode**

### **6. Implementation Plan**

Provide a step‑by‑step plan including:

- Module layout
- Provider registration mechanism
- Testing strategy (unit, integration, replay tests)
- Example workflows:
    - Live tick ingestion
    - Historical candle fetch
    - Normalization pipeline

### **7. Code Examples**

- Provide clean, modular, functional‑style Python code.
- Avoid OOP unless explicitly necessary.
- Use pure functions for parsing and normalization.
- Use dependency injection via configuration objects.
- Include examples for:
    - Provider implementation (e.g., Binance)
    - Unified controller orchestrator
    - Event emission

### **8. Deliverables**

- Provider interface definitions
- Example code modules
- Testing plan
- Integration notes for downstream components
