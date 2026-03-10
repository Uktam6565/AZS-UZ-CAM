\# GasQ System Architecture



GasQ is a Queue Management System for Gas Stations.



Drivers join a queue remotely before arriving at a station.

Operators call drivers to specific pumps.

Realtime updates ensure queue transparency.



---



\# High Level Architecture



&nbsp;                   +----------------------+

&nbsp;                   |      Driver App      |

&nbsp;                   | (Mobile / Web App)   |

&nbsp;                   +----------+-----------+

&nbsp;                              |

&nbsp;                              | REST API

&nbsp;                              |

&nbsp;                   +----------v-----------+

&nbsp;                   |      GasQ Backend    |

&nbsp;                   |      FastAPI API     |

&nbsp;                   +----------+-----------+

&nbsp;                              |

&nbsp;           +------------------+------------------+

&nbsp;           |                                     |

&nbsp;           |                                     |

&nbsp;    +------v------+                       +------v------+

&nbsp;    |  Operator   |                       |  Realtime   |

&nbsp;    |  Dashboard  |                       |  WebSocket  |

&nbsp;    | (Station UI)|                       |   Updates   |

&nbsp;    +------+------+                       +------+------+

&nbsp;           |                                     |

&nbsp;           | REST API                             |

&nbsp;           |                                     |

&nbsp;           +------------------+------------------+

&nbsp;                              |

&nbsp;                              v

&nbsp;                   +----------+-----------+

&nbsp;                   |      PostgreSQL      |

&nbsp;                   |        Database      |

&nbsp;                   +----------+-----------+

&nbsp;                              |

&nbsp;                +-------------+-------------+

&nbsp;                |                           |

&nbsp;        +-------v-------+           +-------v-------+

&nbsp;        | Notifications |           |   Analytics   |

&nbsp;        | SMS / Push    |           | Reports / KPI |

&nbsp;        +---------------+           +---------------+



---



\# Backend Structure



backend/app



main.py  

api/  

models/  

services/  

core/  

db/



---



\# Main Components



\## Driver App



Drivers can:



join queue  

check queue position  

receive notifications  

navigate to assigned pump



---



\## Operator Dashboard



Operators can:



view station queue  

call next driver  

assign pump number  

monitor fueling progress



---



\## Backend API (FastAPI)



Handles:



authentication  

queue management  

driver check-in  

pump assignment  

notifications  

reports



---



\## Realtime System



WebSocket-based queue updates.



Events broadcasted:



ticket\_called  

queue\_updated  

ticket\_done



Frontend dashboards subscribe to station channels.



Example:



/ws/queue/{station\_id}



---



\## Database



PostgreSQL stores:



users  

stations  

pumps  

queue tickets  

reservations  

notifications  

ratings  

audit logs



---



\# Monitoring



Prometheus metrics



HTTP requests  

request latency  

system health



---



\# Logging



Structured logging implemented.



Each request contains:



request\_id  

endpoint  

latency  

status code



---



\# Deployment Target



Planned infrastructure:



Hetzner Cloud



Docker containers:



backend  

postgres  

nginx



---



\# Final Goal



GasQ system must support:



multiple gas stations  

real-time queue updates  

operator pump assignment  

driver notifications  

queue analytics



System must be stable and production ready.

