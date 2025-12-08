-- MySQL dump 10.13  Distrib 8.0.39, for Win64 (x86_64)
--
-- Host: localhost    Database: emr_system
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `patients`
--

DROP TABLE IF EXISTS `patients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patients` (
  `patient_id` int NOT NULL AUTO_INCREMENT,
  `patient_name` varchar(100) DEFAULT NULL,
  `cnic` varchar(20) DEFAULT NULL,
  `nationality` varchar(50) DEFAULT NULL,
  `address` text,
  `phone` varchar(20) DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `age` int DEFAULT NULL,
  PRIMARY KEY (`patient_id`),
  UNIQUE KEY `cnic` (`cnic`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `patients`
--

LOCK TABLES `patients` WRITE;
/*!40000 ALTER TABLE `patients` DISABLE KEYS */;
INSERT INTO `patients` VALUES (1,'Muhammad Umer','42101-7952756-1','Pakistani','North Nazimabad','03332126910','Male',21),(2,'Maulwi abdul','42101-7952766-9','Afghani','My heart','03332127190','Male',69),(3,'test_01','232423423423422','Indian spy','1600, Pennsylvania Avenue','+913302454324','Male',34),(4,'1234','abcf','','','kabdkabf','',0),(6,'umer','00000-0000000-0','adsda','asdad','03332125910','Male',60),(7,'Haris','42101-7952781-1','pakistani','nazimabad','03332125910','Male',21),(8,'zobiah','42101-7986351-1','pakistani','saddar','03032160458','Female',24),(9,'john doe','43234-3234543-2','pakistani','adsd, karachi','03302488308','Male',34),(10,'alex','12345-6789012-3','Pakistan','asd cvbnmjkldfghjkl','01234567892','Male',20),(11,'xyz','12365-4789654-1','Pakistan','asdfghjkl;xcvbnm,.dfghjkl','01236547895','Male',20);
/*!40000 ALTER TABLE `patients` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock`
--

DROP TABLE IF EXISTS `stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock` (
  `key` varchar(255) NOT NULL,
  `generic` varchar(255) DEFAULT NULL,
  `brand` varchar(255) DEFAULT NULL,
  `dosage_form` varchar(255) DEFAULT NULL,
  `dose` varchar(100) DEFAULT NULL,
  `expiry` date DEFAULT NULL,
  `unit` varchar(50) DEFAULT NULL,
  `stock_qty` int DEFAULT NULL,
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock`
--

LOCK TABLES `stock` WRITE;
/*!40000 ALTER TABLE `stock` DISABLE KEYS */;
INSERT INTO `stock` VALUES ('aminophylline plus compound syrup||aminollin','Aminophylline Plus Compound Syrup','Aminollin','Syp','120ml',NULL,'bottles',7),('amoxicillin||novomax','Amoxicillin','Novomax','Capsule','500mg',NULL,'capsules',354),('artemether||gen-m','Artemether','Gen-M','Powd Sus','15+90mg/5ml',NULL,'bottles',15),('azithromycin||azure','Azithromycin','Azure','Tab','500mg',NULL,'tablets',3),('azithromycin||jsk ocen','Azithromycin','Jsk Ocen','Powd Sus','200mg/5ml',NULL,'bottles',1),('azithromycin||zicure','Azithromycin','Zicure','Capsule','250mg',NULL,'capsules',42),('cetrizine||rex','Cetrizine','Rex','Tab','10mg',NULL,'tablets',225),('co-amoxiclav||clav-d','Co-Amoxiclav','Clav-D','Powd Sus','312.5/5ml',NULL,'bottles',1),('levocetirizine dihydrochloride||alvigo','Levocetirizine Dihydrochloride','Alvigo','Tab','5mg',NULL,'tablets',113),('loratidine||lorgy','Loratidine','Lorgy','Syp','5mg/5ml',NULL,'bottles',8),('loratidine||lortec','Loratidine','Lortec','Syp','60ml',NULL,'bottles',33),('monteleukast sodium||zetaleukast','Monteleukast Sodium','Zetaleukast','Tab','10mg',NULL,'tablets',28);
/*!40000 ALTER TABLE `stock` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `visits`
--

DROP TABLE IF EXISTS `visits`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visits` (
  `visit_id` int NOT NULL AUTO_INCREMENT,
  `patient_id` int DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `age` int DEFAULT NULL,
  `doctor_type` varchar(50) DEFAULT NULL,
  `doctor_name` varchar(100) DEFAULT NULL,
  `visit_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `history` text,
  `bp` varchar(20) DEFAULT NULL,
  `bp_systolic` int DEFAULT NULL,
  `bp_diastolic` int DEFAULT NULL,
  `heart_rate` int DEFAULT NULL,
  `sat_o2` int DEFAULT NULL,
  `temp` float DEFAULT NULL,
  `resp_rate` int DEFAULT NULL,
  `blood_glucose` float DEFAULT NULL,
  `symptoms` text,
  `indications` text,
  `medicines` text,
  `dispensed` varchar(5) DEFAULT 'No',
  `dispensed_details` text,
  PRIMARY KEY (`visit_id`),
  KEY `patient_id` (`patient_id`),
  CONSTRAINT `visits_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `visits`
--

LOCK TABLES `visits` WRITE;
/*!40000 ALTER TABLE `visits` DISABLE KEYS */;
INSERT INTO `visits` VALUES (1,2,'Male',69,'Dermatologist',NULL,'2025-11-01 15:25:32','weird','89/80',NULL,NULL,80,89,45,89,80,'weight loss','A001    Cholera due to Vibrio cholerae 01, biovar eltor','Aminophylline Plus Compound Syrup [Aminollin] (2, Morning, 2)','Yes','Aminophylline Plus Compound Syrup — Aminollin => 1 (remaining 7)'),(2,3,'Male',34,'Dermatologist',NULL,'2025-11-01 16:28:40','sothey have removed henry cavil from witcher\'s season 4','66/110',NULL,NULL,99,5,35,5,3,'weight loss','A001    Cholera due to Vibrio cholerae 01, biovar eltor','Azithromycin [Azure] (345, , )','Yes','Azithromycin — Azure => 7 (remaining 3)'),(3,4,'',0,'Dermatologist',NULL,'2025-11-01 16:59:56','','9999/9999990',NULL,NULL,99999999,0,25,9999999,10000000,'fever; shortness of breath','A0102   Typhoid fever with heart involvement; A009    Cholera, unspecified; A001    Cholera due to Vibrio cholerae 01, biovar eltor','Cetrizine [Rex] (, , ); Co-Amoxiclav [Clav-D] (, , ); Azithromycin [Azure] (, , ); Co-Amoxiclav [Clav-D] (, , )','No',''),(4,7,'Male',21,'Cardiologist',NULL,'2025-11-10 16:49:01','Heart attack','190/30',NULL,NULL,88,99,45,88,99,'fever; weight loss','A014    Paratyphoid fever, unspecified; A000    Cholera due to Vibrio cholerae 01, biovar cholerae','Amoxicillin [Novomax] (2, Morning, 3); Loratidine [Lorgy] (4, Evening, 1)','Yes','Amoxicillin — Novomax => 3 (remaining 354); Loratidine — Lorgy => 1 (remaining 8)'),(5,8,'Female',24,'Gynecologist',NULL,'2025-11-10 17:43:38','Heart Attack','120/70',NULL,NULL,88,99,35,88,99,'fatigue; poor appetite; right-sided fever','A0103   Typhoid pneumonia','Cetrizine [Rex] (2, Morning, 3); Co-Amoxiclav [Clav-D] (1, Evening, 1)','Yes','Cetrizine — Rex => 3 (remaining 225); Co-Amoxiclav — Clav-D => 1 (remaining 1)');
/*!40000 ALTER TABLE `visits` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-08 19:31:42
