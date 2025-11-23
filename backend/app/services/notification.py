from apprise import Apprise
from typing import Optional


class NotificationService:
    """Service for sending notifications via Apprise"""
    
    def __init__(self, apprise_url: Optional[str] = None):
        self.apprise_url = apprise_url
        self.apprise = Apprise()
        
        if apprise_url:
            self.apprise.add(apprise_url)
    
    def is_configured(self) -> bool:
        """Check if notification service is configured"""
        return self.apprise_url is not None and len(self.apprise) > 0
    
    async def send_recipe(
        self, 
        recipe_text: str, 
        title: str = "Recipe from Elzar 🌶️"
    ) -> bool:
        """
        Send a recipe notification
        
        Args:
            recipe_text: The recipe content
            title: Notification title
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            raise Exception("Notification service not configured")
        
        try:
            # Truncate recipe if too long for notification
            # Most services have character limits
            max_length = 1000
            if len(recipe_text) > max_length:
                body = recipe_text[:max_length] + "\n\n... (truncated, see full recipe in app)"
            else:
                body = recipe_text
            
            # Send notification
            success = self.apprise.notify(
                title=title,
                body=body
            )
            
            return success
            
        except Exception as e:
            raise Exception(f"Error sending notification: {str(e)}")
    
    def update_config(self, apprise_url: str):
        """Update the Apprise configuration"""
        self.apprise_url = apprise_url
        self.apprise.clear()
        if apprise_url:
            self.apprise.add(apprise_url)

