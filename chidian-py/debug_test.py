#!/usr/bin/env python3

from chidian.mapper import Mapper
from chidian.lib.types import DROP

def debug_drop_operations():
    print("=== Debug DROP Operations ===")
    
    def debug_map(data):
        return {
            "level1": {
                "level2": {
                    "level3": {
                        "trigger_drop": DROP.GRANDPARENT,
                        "wont_appear": "value"
                    },
                    "also_wont_appear": "value"  
                },
                "this_will_be_gone_too": "value"
            },
            "this_stays": "safe"
        }
    
    mapper = Mapper(debug_map)
    result = mapper({})
    
    print("Result:", result)
    print()
    
    # Test simpler case
    def simple_parent_drop(data):
        return {
            "keep": "value",
            "parent": {
                "child": DROP.PARENT
            }
        }
    
    mapper2 = Mapper(simple_parent_drop)
    result2 = mapper2({})
    print("Simple parent drop result:", result2)
    
    # Test grandparent with clearer naming
    def clear_grandparent_drop(data):
        return {
            "root": {
                "parent": {
                    "child": {
                        "trigger": DROP.GRANDPARENT  # Should drop "parent"
                    }
                }
            },
            "sibling": "stays"
        }
    
    mapper3 = Mapper(clear_grandparent_drop)
    result3 = mapper3({})
    print("Clear grandparent drop result:", result3)
    
    # Test the failing deeply nested case
    def deeply_nested_map(data):
        return {
            "app": {
                "modules": {
                    "auth": {
                        "config": {
                            "drop_modules": DROP.GRANDPARENT,  # Should drop 'modules'
                            "secret": "hidden"
                        }
                    },
                    "api": {
                        "routes": ["user", "admin"]
                    }
                },
                "database": {
                    "connection": {
                        "host": "localhost",
                        "drop_database": DROP.PARENT  # Should drop 'database'
                    }
                },
                "settings": {
                    "theme": "dark"
                }
            }
        }
    
    print("\n=== Deeply Nested Case ===")
    mapper4 = Mapper(deeply_nested_map)
    result4 = mapper4({})
    print("Deeply nested result:", result4)
    
    # Let's test each DROP operation separately
    def test_modules_drop_only(data):
        return {
            "app": {
                "modules": {
                    "auth": {
                        "config": {
                            "drop_modules": DROP.GRANDPARENT,  # Should drop 'modules'
                            "secret": "hidden"
                        }
                    },
                    "api": {
                        "routes": ["user", "admin"]
                    }
                },
                "settings": {
                    "theme": "dark"
                }
            }
        }
    
    print("\n=== Test modules drop only ===")
    mapper5 = Mapper(test_modules_drop_only)
    result5 = mapper5({})
    print("Modules drop only result:", result5)
    
    def test_database_drop_only(data):
        return {
            "app": {
                "database": {
                    "connection": {
                        "host": "localhost",
                        "drop_database": DROP.PARENT  # Should drop 'database'
                    }
                },
                "settings": {
                    "theme": "dark"
                }
            }
        }
    
    print("\n=== Test database drop only ===")
    mapper6 = Mapper(test_database_drop_only)
    result6 = mapper6({})
    print("Database drop only result:", result6)

if __name__ == "__main__":
    debug_drop_operations() 