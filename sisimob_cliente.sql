BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "sisimob_cliente" (
	"id"	integer NOT NULL,
	"tipo"	varchar(20) NOT NULL,
	"nome"	varchar(100) NOT NULL,
	"nacionalidade"	varchar(100),
	"profissao"	varchar(100),
	"estado_civil"	varchar(20),
	"telefone"	varchar(15),
	"celular"	varchar(15),
	"email"	varchar(254),
	"pix_modalidade"	varchar(20),
	"chave_pix"	varchar(100),
	"banco"	varchar(100),
	"agencia"	varchar(100),
	"conta_corrente"	varchar(100),
	"poupanca"	varchar(100),
	"cep"	varchar(10) NOT NULL,
	"endereco"	varchar(255) NOT NULL,
	"numero"	varchar(10) NOT NULL,
	"complemento"	varchar(100),
	"bairro"	varchar(100),
	"cidade"	varchar(100) NOT NULL,
	"estado"	varchar(2) NOT NULL,
	"CPF"	varchar(14),
	"rg_rne"	varchar(20) UNIQUE,
	"asaas_id"	varchar(50),
	"cnpj"	varchar(18),
	"documento"	varchar(100),
	"nome_fantasia"	varchar(255),
	"razao_social"	varchar(255),
	"tipo_pessoa"	varchar(1) NOT NULL,
	"regime_casamento"	varchar(30),
	"anuente_id"	bigint,
	"representante_legal_id"	bigint,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("representante_legal_id") REFERENCES "sisimob_cliente"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("anuente_id") REFERENCES "sisimob_cliente"("id") DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO "sisimob_cliente" VALUES (1,'Anuente','Cinthia Rosa de Souza','Brasileiro(a)','Técnico(a) de RX','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03408-020','Rua Santa Gertrudes','211',NULL,'Chácara Santo Antônio (Zona Leste)','São Paulo','SP',NULL,NULL,'cus_000006610422',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (2,'Inquilino','Cledson Alves de Souza','Brasileiro(a)','Analista Contábil','Casado',NULL,'5511985748927',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03408-020','Rua Santa Gertrudes','211',NULL,'Chácara Santo Antônio (Zona Leste)','São Paulo','SP','393.226.788-52','46.298.444','cus_000006610424',NULL,NULL,NULL,NULL,'F','comunhao_parcial',1,NULL);
INSERT INTO "sisimob_cliente" VALUES (3,'Proprietario','Ilda Fonseca de Almeida','Português(a)','Aposentado(a)','Casado',NULL,'5511985748927',NULL,NULL,NULL,'Itaú','0709','66591-3',NULL,'03358-140','Rua Jacaracanga','211','Apto 132','Vila Formosa','São Paulo','SP','19850628871','W2968328','cus_000006611198',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (4,'Proprietario','José João Mecchi','Brasileiro(a)','Vendedor','Viuvo',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03333-055','Travessa Canto da Veronica','6',NULL,'Jardim Anália Franco','São Paulo','SP','02267789833','158786658','cus_000006612095',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (5,'Inquilino','Renato Batalha da Silva Cordeiro','Brasileiro(a)','Projetista','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03333-055','Travessa Canto da Veronica','6',NULL,'Jardim Anália Franco','São Paulo','SP','214.093.328-10',NULL,'cus_000006612211',NULL,NULL,NULL,NULL,'F','separacao_total',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (7,'Inquilino','Thaina Capellani Agostinho','Brasileiro(a)','Corretor(a) de Seguros','Solteiro',NULL,'5511983492444','thainacapellani@gmail.com',NULL,NULL,NULL,NULL,NULL,NULL,'03336-000','Rua Emília Marengo','626','Casa 2','Vila Regente Feijó','São Paulo','SP','447.962.298-50','3766081-6','cus_000006617171',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (8,'Proprietario','Leandro Aparecido Safiotti','Brasileiro(a)','Empresário(a)','Casado',NULL,'5511981876504',NULL,'cpf','114.199.998-69',NULL,NULL,NULL,NULL,'03414-010','Rua São Constâncio','72','Apartamento 61','Vila Mafra','São Paulo','SP','114.199.998-69','16198806-4','cus_000006669268',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (9,'Inquilino','Walter Zago Ujvari','Brasileiro(a)','Empresário(a)','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'08790-040','Rua Prefeito Epaminondas Freire','276',NULL,'Vila Oliveira','Mogi das Cruzes','SP','901.470.908-06','7807171-9','cus_000006669272',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (10,'Proprietario','Fernanda de Freitas Correa Vieira','Brasileiro(a)','Empresário(a)','Casado',NULL,NULL,'socienco.proj@sili.com.br',NULL,NULL,NULL,NULL,NULL,NULL,'03310-000','Rua Itapura','488',NULL,'Vila Gomes Cardim','São Paulo','SP','250.270.538-00','29144584-6','cus_000006670628',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (11,'Inquilino','Elenice Claudino de Freitas','Brasileiro(a)','Empresário(a)','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03310-000','Rua Itapura','488',NULL,'Vila Gomes Cardim','São Paulo','SP','093.614.888-80','18311673-2','cus_000006670631',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (12,'Proprietario','Teresinha Mauricio Cabral','Brasileiro(a)','Do Lar','Solteiro',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03322-001','Rua Azevedo Soares','803','Apartamento 21','Vila Gomes Cardim','São Paulo','SP','089.228.788-86','17424271-2','cus_000006674252',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (13,'Inquilino','Auzenir Pereira dos Santos','Brasileiro(a)','Aposentado(a)','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03322-000','Rua Azevedo Soares','803','Apartamento 21','Vila Gomes Cardim','São Paulo','SP','940.599.778-53','10553063-3','cus_000006674257',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (14,'Anuente','Angélica Giolo Ambrosio','Brasileiro(a)','Assistente Administrativa','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03428-000','Rua Xiririca','1016',NULL,'Vila Carrão','São Paulo','SP','406.779.848-20','48055979-X','cus_000006674272',NULL,NULL,NULL,NULL,'F','comunhao_total',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (15,'Inquilino','Daniel Almeida Gomes','Brasileiro(a)','Engenheiro(a) de Sistemas','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03428-000','Rua Xiririca','1016',NULL,'Vila Carrão','São Paulo','SP','371.078.548-01','46163775-3','cus_000006674277',NULL,NULL,NULL,NULL,'F','separacao_total',14,NULL);
INSERT INTO "sisimob_cliente" VALUES (16,'Proprietario','Sonia Verginia de Lima Forestiero','Brasileiro(a)','Comerciante','Divorciado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03428-000','Rua Xiririca','1016',NULL,'Vila Carrão','São Paulo','SP','076.895.338-33','13453144-9','cus_000006674281',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (17,'Proprietario','Sandra Aparecida Minas','Brasileiro(a)','Do Lar','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03322-001','Rua Azevedo Soares','1451','A','Vila Gomes Cardim','São Paulo','SP','008.261.368-00','1178229-1','',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (18,'Inquilino','Luigi Pinto','Brasileiro(a)','Aposentado(a)','Divorciado',NULL,'5511995972506',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03322-001','Rua Azevedo Soares','1451','A','Vila Gomes Cardim','São Paulo','SP','012.313.108-12','854403-8','cus_000118075304',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (19,'Inquilino','Maria Socorro Medeiros','Brasileiro(a)','Aposentado(a)','Divorciado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03408-020','Rua Santa Gertrudes','207','Casa 5','Chácara Santo Antônio (Zona Leste)','São Paulo','SP','221.276.904-00','56191224-5','cus_000117878629',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (20,'Inquilino','Wilson Monteiro do Nascimento','Brasileiro(a)','Advogado(a)','Casado',NULL,'5511996061545',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03323-040','Rua Coelho Lisboa','61','Sala 102','Cidade Mãe do Céu','São Paulo','SP','032.456.308-67','1352464-1','cus_000118075677',NULL,NULL,NULL,NULL,'F','comunhao_total',21,NULL);
INSERT INTO "sisimob_cliente" VALUES (21,'Anuente','Marcia dos Santos Monteiro','Brasileiro(a)','Empresário(a)','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03323-040','Rua Coelho Lisboa','61','Sala 102','Cidade Mãe do Céu','São Paulo','SP','090.776.748-61','20110102-6','cus_000117879119',NULL,NULL,NULL,NULL,'F','comunhao_total',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (22,'Anuente','Roberta Ferreira Ventura','Brasileiro(a)','Do Lar','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03358-110','Rua Gonçalo Coelho','40',NULL,'Vila Formosa','São Paulo','SP','921.966.673-15','59679517-8','cus_000117884272',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (23,'Representante Legal','Amir Al Jbawi','Sírio(a)','Empresário(a)','Casado',NULL,'5511956505525',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03358-110','Rua Gonçalo Coelho','40',NULL,'Vila Formosa','São Paulo','SP','237.084.148-61','67080853-2','cus_000117884289',NULL,NULL,NULL,NULL,'F','comunhao_parcial',22,NULL);
INSERT INTO "sisimob_cliente" VALUES (24,'Inquilino','Amir Al Jbawi 23708414861',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03035-000','Avenida Bom Jardim','110',NULL,'Pari','São Paulo','SP',NULL,NULL,'cus_000117884436','42.219.793/0001-84',NULL,'Qassioun Sweeets','Amir Al Jbawi 23708414861','J',NULL,NULL,23);
INSERT INTO "sisimob_cliente" VALUES (25,'Proprietario','José Renato Fonseca de Almeida','Brasileiro(a)','Produtor(a) Cultural','Solteiro',NULL,'5511992398687',NULL,'cpf','127.954.978-59',NULL,NULL,NULL,NULL,'03358-110','Rua Gonçalo Coelho','40',NULL,'Vila Formosa','São Paulo','SP','127.954.978-59','19566690-2','cus_000117884809',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (26,'Inquilino','Elaine Cristina Viana da Silva','Brasileiro(a)','Atendente','Solteiro','11995972506','5511949235702',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03408-020','Rua Santa Gertrudes','207','Casa 3','Chácara Santo Antônio (Zona Leste)','São Paulo','SP','342.622.388-06','42932016-4','cus_000117888836',NULL,NULL,'Elenita Barreto',NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (27,'Inquilino','Gabriel Henrique dos Santos','Brasileiro(a)','Empresário(a)','Solteiro',NULL,'5511998291813',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03408-020','Rua Santa Gertrudes','207','Casa 2','Chácara Santo Antônio (Zona Leste)','São Paulo','SP','479.756.758-90','5833944-5','cus_000117889412',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (28,'Inquilino','Arlete Rodrigues Ferreira','Brasileiro(a)','Aposentado(a)','Solteiro',NULL,'5511986896440',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03408-020','Rua Santa Gertrudes','207','Casa 1','Chácara Santo Antônio (Zona Leste)','São Paulo','SP','046.956.678-78','955998-5','cus_000117890341',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (29,'Representante Legal','Claudemir Izidio Ferreira','Brasileiro(a)','Empresário(a)','Viuvo',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03322-001','Rua Azevedo Soares','1350',NULL,'Vila Gomes Cardim','São Paulo','SP','060.125.878-99',NULL,'cus_000117890435',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (30,'Fiador(a)','Theon Corretora de Seguros e Negócios Imobiliários',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03322-001','Rua Azevedo Soares','1350',NULL,'Vila Gomes Cardim','São Paulo','SP',NULL,NULL,'cus_000117890511','01.445.201/0001-65',NULL,'Theon Seguros',NULL,'J',NULL,NULL,29);
INSERT INTO "sisimob_cliente" VALUES (31,'Proprietario','Renata Solyom Morais Pomelli','Brasileiro(a)','Educador(a)','Casado',NULL,'5511975402208',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03573-010','Rua Costeira','291',NULL,'Jardim Arize','São Paulo','SP','307.470.118-85','3227375-1','cus_000117916329',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (32,'Inquilino','Patrícia de Sousa Rosa','Brasileiro(a)','Empresário(a)','Divorciado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03573-010','Rua Costeira','291',NULL,'Jardim Arize','São Paulo','SP','332.534.668-50','44310802-X','cus_000117916358',NULL,NULL,NULL,NULL,'F',NULL,NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (33,'Proprietario','Valéria Barreto Nogueira','Brasileiro(a)','Do Lar','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03334-050','Rua Sebastião Barbosa','133','Apartamento 42','Vila Regente Feijó','São Paulo','SP',NULL,NULL,'cus_000117966818',NULL,NULL,NULL,NULL,'F','comunhao_parcial',NULL,NULL);
INSERT INTO "sisimob_cliente" VALUES (34,'Proprietario','Carlos Humberto Nogueira','Brasileiro(a)','Administrador(a) de Empresas','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03334-050','Rua Sebastião Barbosa','133','Apartamento 42','Vila Regente Feijó','São Paulo','SP','379.319.208-30','5233573-2','cus_000117943458',NULL,NULL,NULL,NULL,'F','comunhao_parcial',33,NULL);
INSERT INTO "sisimob_cliente" VALUES (35,'Inquilino','Mauro Sérgio Pereira Lacerda','Brasileiro(a)','Funcionário(a) Publico(a)','Casado',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'03334-050','Rua Sebastião Barbosa','133','Apartamento 42','Vila Regente Feijó','São Paulo','SP','112.742.898-58','2166485-8','cus_000117943555',NULL,NULL,NULL,NULL,'F','separacao_total',NULL,NULL);
CREATE INDEX IF NOT EXISTS "sisimob_cliente_anuente_id_539763da" ON "sisimob_cliente" (
	"anuente_id"
);
CREATE INDEX IF NOT EXISTS "sisimob_cliente_representante_legal_id_47dbd38a" ON "sisimob_cliente" (
	"representante_legal_id"
);
COMMIT;
