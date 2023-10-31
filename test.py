   database_name = fields.Char(string='Database Name')

    @api.onchange('mobile')
    def update_mobile(self):
        self.sync_mobile_with_external()

    def sync_mobile_with_external(self):
        # Get the database credentials associated with this Odoo instance
        cred = self.env['credential.credentials'].search([("company", '=', self.company_id.id)])
        
        if not cred:
            _logger.error("Database credentials not found for this company.")
            return

        # Establish a connection to the external database
        up_cnx = mysql.connector.connect(
            user=cred.user,
            password=cred.password,
            host=cred.host,
            database=cred.database,
            raw=True
        )

        try:
            # Construct and execute the SQL update query
            mycursorUpdate = up_cnx.cursor()
            update_query = (
                "UPDATE `gibbonPerson` "
                "SET `emergency1Number1` = %s "
                "WHERE `gibbonPersonID` = %s"
            )
            values = (str(self.mobile), str(self.gibbon_person_ID))
            mycursorUpdate.execute(update_query, values)
            up_cnx.commit()
        except mysql.connector.Error as err:
            _logger.error(f"Error updating mobile in external database: {err}")
        finally:
            up_cnx.close()

class CredentialCredentials(models.Model):
    _name = 'credential.credentials'

    user = fields.Char(string="User", required=True)
    password = fields.Char(string="Password", required=True)
    host = fields.Char(string="Host", required=True)
    database = fields.Char(string="Database", required=True)
    company = fields.Many2one("res.company", string="Company", required=True)

    def get_db_connection(self):
        return mysql.connector.connect(user=self.user, password=self.password,
                                        host=self.host, database=self.database, raw=True)
    def custom_res(self, cred):
        cnx = self.get_db_connection()
        db_name = cred.database

        mycursor = cnx.cursor()
        sql_query = "SELECT gp.gibbonPersonID, gp.officialName, gp.status, gp.emergency1Number1, gp.gibbonRoleIDPrimary, gp.dateStart, gp.dateEnd, gyg.name, gfg.name FROM gibbonPerson AS gp " \
                    "LEFT JOIN gibbonStudentEnrolment AS gse ON gse.gibbonPersonID = gp.gibbonPersonID " \
                    "LEFT JOIN gibbonYearGroup AS gyg ON gyg.gibbonYearGroupID = gse.gibbonYearGroupID " \
                    "LEFT JOIN gibbonFormGroup AS gfg ON gfg.gibbonFormGroupID = gse.gibbonFormGroupID " \
                    "WHERE gp.gibbonRoleIDPrimary = '003'"
        mycursor.execute(sql_query)
        myresult = mycursor.fetchall()

        for x in myresult:
            try:
                partner_obj = self.env['res.partner']
                existing_record = partner_obj.search([('gibbon_person_ID', '=', str(x[0].decode('utf-8'))),('database_name', '=', str(db_name))])

                if not existing_record:
                    partner_obj.create({
                        "gibbon_person_ID": x[0] if x[0] else '',
                        "name": x[1] if x[1] else '',
                        "status": x[2] if x[2] else '',
                        "role_id": x[4] if x[4] else '',
                        "start_date": x[5] if x[5] else '',
                        "end_date": x[6] if x[6] else '',
                        "year_group": x[7] if x[7] else '',
                        "form_group": x[8] if x[8] else '',
                        "company_id": cred.company.id,
                        "database_name": db_name
                    })
                else:
                    # Handle updating existing records
                    pass

            except Exception as e:
                _logger.error(f"Error syncing data for {cred.database}: {e}")
            finally:
                cnx.close()
