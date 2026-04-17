"""OpenAPI 3.1 spec for the public REST API.

Served as JSON at /api/v1/openapi.json and rendered as Swagger UI at
/docs/api. Kept in a dedicated module so the Blueprint file stays focused on
behaviour.
"""

from flask import request


def build_openapi_spec() -> dict:
    base = request.url_root.rstrip("/")
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "LandRegistry.company API",
            "version": "1.0.0",
            "summary": "Search UK Land Registry CCOD/OCOD company ownership data.",
            "description": (
                "Public REST API for looking up properties owned by UK and "
                "overseas companies, and for resolving directors to their "
                "portfolio of properties. Authenticate with a bearer API key "
                "minted at /developers. Billing uses prepaid API credits "
                "purchased via Stripe — separate from the web-UI credit pool."
            ),
            "contact": {"url": "https://landregistry.company"},
            "license": {"name": "Proprietary"},
        },
        "servers": [{"url": f"{base}/api/v1"}],
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "lr_live_...",
                    "description": (
                        "Pass `Authorization: Bearer <api_key>` on every "
                        "request. Keys start with `lr_live_` and are minted "
                        "on the developer dashboard."
                    ),
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                                "request_id": {"type": "string"},
                            },
                        }
                    },
                },
                "Property": {
                    "type": "object",
                    "properties": {
                        "title_number": {"type": "string"},
                        "tenure": {"type": "string"},
                        "property_address": {"type": "string"},
                        "district": {"type": "string"},
                        "county": {"type": "string"},
                        "region": {"type": "string"},
                        "postcode": {"type": "string"},
                        "price_paid": {"type": "string"},
                        "date_proprietor_added": {"type": "string"},
                        "proprietor_name": {"type": "string"},
                        "company_registration_no": {"type": "string"},
                        "proprietorship_category": {"type": "string"},
                        "country_incorporated": {"type": "string", "nullable": True},
                        "address_line_1": {"type": "string"},
                        "address_line_2": {"type": "string"},
                        "address_line_3": {"type": "string"},
                        "data_source": {
                            "type": "string",
                            "enum": ["CCOD", "OCOD"],
                        },
                    },
                },
                "Pagination": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "offset": {"type": "integer"},
                        "returned": {"type": "integer"},
                        "has_more": {"type": "boolean"},
                    },
                },
                "PropertyList": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "object"},
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Property"},
                        },
                        "pagination": {"$ref": "#/components/schemas/Pagination"},
                    },
                },
            },
            "parameters": {
                "Limit": {
                    "name": "limit",
                    "in": "query",
                    "schema": {"type": "integer", "default": 50, "maximum": 500},
                },
                "Offset": {
                    "name": "offset",
                    "in": "query",
                    "schema": {"type": "integer", "default": 0},
                },
            },
            "responses": {
                "Unauthorized": {
                    "description": "Missing or invalid API key.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    },
                },
                "PaymentRequired": {
                    "description": "Insufficient API credits.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    },
                },
                "RateLimited": {
                    "description": "Rate limit exceeded.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    },
                },
            },
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Liveness check (no auth).",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "Service healthy.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "version": {"type": "string"},
                                            "time": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/me": {
                "get": {
                    "summary": "Authenticated account + credit balance.",
                    "responses": {
                        "200": {"description": "Account info."},
                        "401": {"$ref": "#/components/responses/Unauthorized"},
                    },
                }
            },
            "/usage": {
                "get": {
                    "summary": "Recent API requests made with this key.",
                    "parameters": [{"$ref": "#/components/parameters/Limit"}],
                    "responses": {"200": {"description": "List of recent calls."}},
                }
            },
            "/properties/by-company-number": {
                "get": {
                    "summary": "Properties owned by a specific UK company number (1 credit).",
                    "parameters": [
                        {
                            "name": "number",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "example": "09876543",
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Offset"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Matching properties.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/PropertyList"
                                    }
                                }
                            },
                        },
                        "402": {"$ref": "#/components/responses/PaymentRequired"},
                        "429": {"$ref": "#/components/responses/RateLimited"},
                    },
                }
            },
            "/properties/by-company-name": {
                "get": {
                    "summary": "Properties owned by a company matched by name (1 credit).",
                    "parameters": [
                        {
                            "name": "name",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "fuzzy",
                            "in": "query",
                            "schema": {"type": "boolean", "default": True},
                        },
                        {
                            "name": "fuzzy_threshold",
                            "in": "query",
                            "schema": {"type": "integer", "default": 70},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Offset"},
                    ],
                    "responses": {
                        "200": {"description": "Matches + fuzzy suggestions."},
                        "402": {"$ref": "#/components/responses/PaymentRequired"},
                    },
                }
            },
            "/properties/by-address": {
                "get": {
                    "summary": "Properties matching an address or postcode (1 credit).",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Offset"},
                    ],
                    "responses": {"200": {"description": "Matching properties."}},
                }
            },
            "/directors/search": {
                "get": {
                    "summary": "Find individual directors by name via Companies House (1 credit).",
                    "parameters": [
                        {
                            "name": "name",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": (
                                "List of individual officers. Pass the "
                                "`officer_id` into `/directors/properties`."
                            )
                        }
                    },
                }
            },
            "/directors/properties": {
                "get": {
                    "summary": "Properties owned by companies where this director is/was an officer (3 credits).",
                    "parameters": [
                        {
                            "name": "officer_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": (
                                "Pass the `officer_id` field returned by "
                                "/directors/search (e.g. "
                                "`/officers/abcd1234/appointments`)."
                            ),
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Offset"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Appointments + aggregated properties."
                        }
                    },
                }
            },
        },
    }
