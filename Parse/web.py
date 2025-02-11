import pdfcrowd
import sys
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("PDFCROWD_USERNAME")
api_key = os.getenv("PDFCROWD_API_KEY")

try:
    # Create an API client instance
    client = pdfcrowd.HtmlToPdfClient(username, api_key)

    # Specify the mapping of HTML content width to the PDF page width.
    # To fine-tune the layout, you can specify an exact viewport width, such as '960px'.
    # client.setContentViewportWidth('balanced')

    client.setUseHttp(True)
    # Run the conversion and save the result to a file.
    client.convertUrlToFile("https://catalog.wku.edu/undergraduate/science-engineering/engineering-applied-sciences/computer-science-bs/#programrequirementstext", "example2.pdf")
    
except pdfcrowd.Error as why:
    sys.stderr.write('Pdfcrowd Error: {}\n'.format(why))
    raise
