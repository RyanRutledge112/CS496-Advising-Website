import pdfcrowd
import sys

try:
    # Create an API client instance.
    # For now, I will add the 
    client = pdfcrowd.HtmlToPdfClient('pahmeh', '113d1aa4275b559bdb210eeb504fab45')

    # Specify the mapping of HTML content width to the PDF page width.
    # To fine-tune the layout, you can specify an exact viewport width, such as '960px'.
    # client.setContentViewportWidth('balanced')

    client.setUseHttp(True)
    # Run the conversion and save the result to a file.
    client.convertUrlToFile("https://catalog.wku.edu/undergraduate/science-engineering/engineering-applied-sciences/computer-science-bs/#programrequirementstext", "example.pdf")
    
except pdfcrowd.Error as why:
    sys.stderr.write('Pdfcrowd Error: {}\n'.format(why))
    raise
