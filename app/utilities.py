from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

class Utilities_class:
    sender_email = "gunadhya.ai@gmail.com"
    sender_password = "zdsn pelr qywo uexl"
    @staticmethod
    def send_email_ai_response(email : str , query : str):

        subject = "Unresolved Query - AI Chatbot Support Required"
        
        html_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 3px; margin-bottom: 20px; }}
                    .content {{ margin: 15px 0; }}
                    .query-section {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; border-radius: 3px; }}
                    .footer {{ color: #666; font-size: 12px; margin-top: 20px; text-align: center; border-top: 1px solid #ddd; padding-top: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Unresolved Query Notification</h2>
                        <p><strong>Status:</strong> Query Unable to be Resolved by AI Chatbot</p>
                    </div>
                    
                    <div class="content">
                        <p>Dear Support Team,</p>
                        <p>A user has submitted a query to the AI Chatbot system that could not be resolved through the standard knowledge base. Please review the following unresolved query:</p>
                        
                        <div class="query-section">
                            <strong>User Query:</strong>
                            <p>{query}</p>
                        </div>
                        
                        <p><strong>Action Required:</strong></p>
                        <ul>
                            <li>Review the query for relevance and accuracy</li>
                            <li>Update knowledge base if applicable</li>
                            <li>Provide manual support or escalate to relevant department</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>This is an automated notification from the AI Chatbot System.<br/>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg["From"] = Utilities_class.sender_email
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, 'html'))

        try:
            server = smtplib.SMTP('smtp.gmail.com' , 587)
            server.starttls()
            server.login(Utilities_class.sender_email , Utilities_class.sender_password)
            server.send_message(msg)
            print("Mail send")
        except Exception as e:
            raise Exception(f"Email not send" , {e})