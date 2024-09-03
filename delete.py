def generate_email_content(recipient_email, png_csv_dict):
    # create the email content
    msg = MIMEMultipart("related")
    msg["Subject"] = "Daily Reports from StockAdvisor"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email

    # create the email body with HTML
    html_content = """
        <html>
        <body>
            <p>Hello,</p>
            <p>Here’s your daily report from StockAdvisor, featuring the latest stock market performance based on the periods you've tracked.</p>
        """

    # iterate over the PNG and CSV file paths
    for png_path, csv_path in zip(png_csv_dict['png'], png_csv_dict['csv']):
        if os.path.isfile(png_path):  # check if PNG path is a file
            try:
                # attach the PNG image to the email body
                with open(png_path, "rb") as f:
                    img_data = f.read()
                    img_type = os.path.splitext(png_path)[1][1:]  # get image file type (e.g., 'png')
                    img_name = os.path.basename(png_path)

                    # create an image MIME part
                    img_part = MIMEImage(img_data, _subtype=img_type)
                    img_part.add_header("Content-ID", f"<{img_name}>")
                    img_part.add_header("Content-Disposition", "inline", filename=img_name)
                    msg.attach(img_part)

                    # add the image to the HTML content
                    html_content += f'<img src="cid:{img_name}" alt="{img_name}"><br>'

                    print(f"Added image: {png_path}")

            except Exception as e:
                print(f"Failed to include {png_path} in the email body: {e}")

        if os.path.isfile(csv_path):  # check if CSV path is a file
            try:
                # generate the summary HTML table
                table_html = create_summary_html(csv_path)

                # add the HTML table to the email content
                html_content += f'<h3>Summary of Portfolio Performance</h3>{table_html}<br>'

                print(f"Added table from CSV: {csv_path}")

            except Exception as e:
                print(f"Failed to include {csv_path} in the email body: {e}")

    # add the closing content
    html_content += """
            <p>For a more detailed analysis or to adjust your tracked periods, please log in to StockAdvisor.</p>
        </body>
        </html>
    """

    # attach the HTML content to the email
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Debug print the HTML content
    print("Generated HTML content:")
    print(msg.as_string())

    return msg