import os
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import re 
import io
from windwardrestapi.Model import Template, SqlDataSource
from windwardrestapi.Api import WindwardClient as client
import os
import time
import base64
import zipfile

app = Flask(__name__)

app.config['upload_folder'] = os.path.dirname(os.path.abspath(__file__)) + '/uploads/'
app.config['generated_docs_folder'] = os.path.dirname(os.path.abspath(__file__)) + '/generated_docs/'

#email
sender_address = 'babsondiagnostics@gmail.com'
sender_pass = '2o3rok3efk'
s = smtplib.SMTP('smtp.gmail.com', 587) 

allowedFileTypes = {'docx'}

#generating document
windwardClientAddress = "http://localhost:8080/"
datasourceName = "HarvestODBC"
datasourceClassName = "System.Data.Odbc"
datasourceConnectionString = "driver=4D v15 ODBC Driver 64-bit;SERVER=10.0.0.20;PORT=19812;UID=Orchard;pwd=B@bs0nDx!"


def isAllowedFile(filename):
   return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowedFileTypes

def getAllUploadedTemplates():
	files = []
	for file in os.listdir(app.config['upload_folder']):
		if file.endswith(".docx"):
			files.append(file.rsplit('.', 1)[0])
	return files

def generateDocFromTemplate (filename):
	newClient = client.WindwardClient(windwardClientAddress)
	sqlDS = SqlDataSource.SqlDataSource(name=datasourceName, className=datasourceClassName, connectionString=datasourceConnectionString)
	file_path = os.path.abspath(os.path.join(app.config['upload_folder'], filename))
	templatePDF = Template.Template(data=file_path, outputFormat=Template.outputFormatEnum.PDF, datasources=sqlDS)
	generatedDoc = newClient.postDocument(templatePDF)
	while True:
		document_status = newClient.getDocumentStatus(generatedDoc.guid)
		if document_status != 302:
			time.sleep(1)
		else:
			break
	getDocument = newClient.getDocument(generatedDoc.guid)
	new_doc_name = "generated_docs/" + filename.rsplit('.', 1)[0] + ".pdf"
	with open(new_doc_name, "wb") as fh:
		fh.write(base64.standard_b64decode(getDocument.data))


@app.route('/', methods=['GET', 'POST'])
def main_func():
	return redirect(url_for('Templates'))

@app.route('/Templates', methods=['GET', 'POST'])
def Templates():
	if request.method == 'POST':
		if 'uploadNewTemplate' in request.form:
			return render_template('templates.html', display="Upload new template modal", files=getAllUploadedTemplates())
		elif 'uploadedFile' in request.form:
			if 'file' in request.files:
				file = request.files['file']
				if file and file.filename != '' and isAllowedFile(file.filename):
					filename = secure_filename(file.filename)
					file.save(os.path.join(app.config['upload_folder'], filename))
					generateDocFromTemplate(filename)
					return render_template('templates.html', display="Upload success", files=getAllUploadedTemplates())
			return render_template('templates.html', display="Upload failure", files=getAllUploadedTemplates())
		elif 'seeMoreOptions' in request.form or 'goBack' in request.form:
			return render_template('templates.html', display = "More options", file_name=request.form['file_name'], files=getAllUploadedTemplates())
		elif 'downloadTemplate' in request.form:
			return send_from_directory(app.config['upload_folder'], request.form['file_name'] + ".docx", as_attachment=True) 
		elif 'downloadPDF' in request.form:
			return send_from_directory(app.config['generated_docs_folder'], request.form['file_name'] + ".pdf", as_attachment=True) 
		elif 'email' in request.form or 'goBackToEmail' in request.form:
			return render_template('templates.html', display="Create email", file_name=request.form['file_name'], files=getAllUploadedTemplates())
		elif 'emailSend' in request.form:
			recipients = email(request.form)
			return render_template('templates.html', display="Email sent", recipients=recipients, file_name=request.form['file_name'], files=getAllUploadedTemplates())
		elif 'delete' in request.form:
			return render_template('templates.html', display="Confirm delete", file_name=request.form['file_name'], files=getAllUploadedTemplates())
		elif 'deleteConfirmYes' in request.form:
			os.remove(os.path.join(app.config['upload_folder'], request.form['file_name'] + ".docx"))
			os.remove(os.path.join(app.config['generated_docs_folder'], request.form['file_name'] + ".pdf"))
			return render_template('templates.html', display="Deleted", file_name=request.form['file_name'], files=getAllUploadedTemplates())
	return render_template('templates.html', display="Main screen", files=getAllUploadedTemplates())


def email (form):
	recipients = re.findall('[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}', form['recipients'])

	for rec in recipients:
		###creating email
		msg = MIMEMultipart()
		msg['From'] = sender_address
		msg['To'] = rec
		msg['Subject'] = form['subject']
		msg.attach(MIMEText(form['body'], 'plain'))

		#attaching pdf
		with open("generated_docs/" + form['attachment'], "rb") as file:
			docAttachment = MIMEBase("application", "octet-stream")
			docAttachment.set_payload(file.read())
		encoders.encode_base64(docAttachment)

		docAttachment.add_header("Content-Disposition", f"attachment; filename= {form['attachment']}",)
		msg.attach(docAttachment)
		
		###sending email
		s.starttls() 
		s.login(sender_address, sender_pass)
		s.sendmail(sender_address, rec, msg.as_string()) 
		s.quit()
	return recipients

@app.route('/More_Info', methods=['GET', 'POST'])
def More_Info():
	return render_template('more_info.html')

if __name__ == '__main__':
	app.run(host='127.0.0.1', port=8082, debug=True)


