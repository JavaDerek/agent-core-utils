"""Browser utilities for agent applications."""

def initialize_driver():
    """Initialize a browser driver.
    
    This is a stub implementation for CI/testing.
    In production, this should be replaced with actual browser driver initialization.
    """
    # Return a dummy object for CI/testing
    class DummyDriver:
        def quit(self):
            pass
        
        def get(self, url):
            pass
            
        def page_source(self):
            return "<html><body>Test page</body></html>"
    
    return DummyDriver()
