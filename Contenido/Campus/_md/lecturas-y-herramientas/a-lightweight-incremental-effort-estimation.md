# A Lightweight Incremental Effort Estimation

> Fuente PDF: `Lecturas y Herramientas/A Lightweight Incremental Effort Estimation.pdf`
>
> Markdown operativo generado para busqueda y lectura agentica.
> Metodo: `pdftotext -layout`.
> Paginas: 23.
> Palabras extraidas por `pdftotext`: 1779.
> Palabras finales en este Markdown: 1779.
> Nota de calidad: Texto extraible util para busqueda; revisar el PDF fuente para tablas, figuras o maquetacion.

---

A Lightweight Incremental Effort Estimation
    Model For Use Case Driven Projects

                Kan Qi, Dr. Barry Boehm
            University of Southern California
                 {kqi,boehm}@usc.edu
                    Outline
• Background of use case driven approach
• Motivations
• Software sizing models
• Transaction identification and classification
• Size metrics
• Empirical Study
• Conclusions
                      Background
q Use case driven approach of software engineering
   – functional requirements are captured by use cases that define the
     interactions between actors and a system.
   – use cases can be written in textual format as use case narratives or visually
     represented by use case diagrams.
   – system reactions can further be modeled in more detail by robustness
     diagrams, sequence diagrams, and class diagrams.
                             Background
q Existing methods for software sizing and effort estimation
    –   COCOMO II, uses SLOC as the size metric and 22 factors to model the multiplicative
        and exponential effects from the project, personnel, product, and process aspects on
        project effort. The exact effects are calibrated on 161 projects.
    –   Function Points, used as a measure of the units of functionality, which specifically are
        measured by data and transaction functions.
    –   Use Case Points, estimate software size by the number of use cases, weighted by the
        number of transactions.
    –   Story Points, models the relative effort for tasks based on a typical task. Popular with
        agile development.

q Estimate effort at the early stage of a project
   – Schedule and cost estimation
   – Risk management
                           Motivations
q Difficulties in applying other estimation methods to use case driven
  projects
    – Hard to accurately estimate software size in terms of source lines of code,
      unless the estimations are done by experts or for precedential systems.
    – Function Points requires detailed information to determine the
      elementary processes and data elements of different types. It requires
      expertise to achieve a reproducible calculation.
    – Use Case Points involves manual counting process, and may not be
      accurate as a size estimator for not considering the internal complexity of
      the transactions.
    – Story Points is only able to estimate effort of the tasks at local scales, since
      different groups of users may use a different reference task.
                         Motivations
q Our goals
   – To improve the efficiency of the counting process.
   – To deliver an effort estimation model that is compatible with the lifecycle
     of use case driven projects.
   – To improve the accuracy based on information available at different
     phases of the software process.
  Challenges and Approaches

q Lifecycle: Phase-based effort estimation models to provide multiple
   estimations at different phases of the process.
    - Two phases of estimation to keep the balance between utility and accuracy.
    - Information availability assumed based on the typical deliverables of the two
      phases.
q Agility: Size metrics are directly countable from the artifacts of the
   process to avoid investing too much effort in collecting information for
   effort estimation.
    - Automated counting procedures are developed.
q Accuracy: Incrementally integrate information available at the
   different phases of the process to more accurately estimate software
   size.
              Software Sizing Models
q Use Cases
   – Use cases are used to capture the interactions between actors and a system. They are
     usually represented with use case narratives, activity diagrams, robustness diagrams, or
     sequence diagrams.
q Transactions
   – A sequence of interactions between system components, which realizes a basic unit of
     system functionality. Use cases are modeled by a set of transactions.
                                  𝑃𝑟𝑜𝑗𝑒𝑐𝑡 𝑆𝑖𝑧𝑒 = - 𝑤/
                                                   /∈2

q Weighted Transactions
   – As an architecture introduced, the connectors and components of a system are decided,
     so as the internal structure of the transactions. Transactions are weighted by its internal
     structure to represent its contribution to the overall effort.
                              𝑃𝑟𝑜𝑗𝑒𝑐𝑡 𝑆𝑖𝑧𝑒 = - - 𝑤3
                                               /∈2 3∈/
         Transaction Identification and
                 Classification
q Transaction identification
    – For use case narratives, structured scenarios are extracted and converted
      to activity diagrams. The number of transactions are counted as number
      of scenarios, or the number of paths in an activity diagram.
    – For robustness diagrams, each independent path of the directed graph is
      defined as a transaction.
    – For sequence diagrams, the meaningful sequence of messages is defined
      as a transaction.
Transaction Identification Examples


                                              Transactions are as independent paths of robustness
                                              diagrams




 Transactions are as flows of events of   Transactions are as sequences of messages of sequence
 activity diagrams                        diagrams
         Transaction Identification and
                 Classification
q Transaction classification
    – The elements on an independent path represent the internal structure of
      a transaction.
        • number of system components a transaction is implemented upon.
        • the types of the elements, for example, boundary, control, and entity.
    – Transactions are classified into different levels of complexity by the
      number of user interface elements and domain elements.
    – User interface elements (UIE) are defined as identifiable UI components .
    – Domain elements (DE) are defined as the elements on the independent
      paths.



                          Example of transaction classification scheme
                          Size metric - I
q Early Use Case Points (EUCP)
    – Use the number of scenarios to weight the use cases, and sum all the
      weighted use cases to calculate the Unadjusted Early Use Case Weight
      (UEUCW).
        • Transactions are automatically identified from use case narratives through the
          converted activity diagrams.
    – Calculate Unadjusted Actor Weight (UAW) based on the actors identified
      from use case narratives.
    – Evaluate the project for the 13 Technical Complexity Factors (TCF) and 8
      Environmental Factors (EF) from original UCP definition.
    – Calculate EUCP based on:

                𝐸𝑈𝐶𝑃 = 𝑈𝐸𝑈𝐶𝑊 + 𝑈𝐴𝑊 ∗ 𝑇𝐶𝐹 ∗ 𝐸𝐹
                     Size metric - II
q Extended Use Case Points (EXUCP)
   – Transactions are identified as the independent paths of robustness
     diagrams or sequences of messages from sequence diagrams.
   – Use the number of Domain Elements (DE) and UI elements (UIE) that each
     identified transaction interacts with to weight the transaction as the
     Unadjusted Transaction Weight (UTW).
   – Sum the total UTW to calculate Unadjusted Extended Use Case Weight
     (UEXUCW) for the use cases.
   – Reuse the evaluations for UAW, TCF, and EF from size metric – I .
   – Calculate EXUCP by the equation below:


                 𝐸𝑋𝑈𝐶𝑃 = 𝑈𝐸𝑋𝑈𝐶𝑊 + 𝑈𝐴𝑊 ∗ 𝑇𝐶𝐹 ∗ 𝐸𝐹
                    Empirical Study
q Data collection
   – 4 projects from master level software engineering courses (csci577 and
     csci590) from 2014-2017.
   – They are mobile applications or web applications, written in 3rd Gen
     programming languages: PHP, JavaScript, Nodejs, Java, Object-C, etc.
   – The projects are lasted for about 4 – 12 months, and done with teams of
     5-24 people. Delivered software applications ranging from 3-20 KSLOC.
   – 114 use cases were collected in total, including use case narratives,
     robustness diagrams, and sequence diagrams.
   – Effort data were collected through weekly effort reports.
                       Model Calibration
•   Apply the counting processes and algorithms to identify the information
    needed for Early Use case Points (EUCP) and Extended Use Case Points
    (EXUCP).
•   Calculate EUCP and EXUCP for the 4 projects.
•   Normalize Effort.
     – Remove influences from the un-modeled environmental factors.
     – The un-modeled factors are the factors that are modeled by COCOMO II, but not modeled by
       Use Case Points. Detail is provided in the paper.
•   Correlation coefficients are calculated to determine if linear relationships exist
    between the size metrics and normalized effort within the data set.
•   Apply linear regression to calibrate the linear models to understand the exact
    effects the metrics have on project effort.
•   Evaluate the goodness of fit by R? , MMRE, and PRED(.25).
•   Hypothesis tests are applied to understand the significance of the estimates.
              Empirical Results
q Counting results for the four sample projects




q Actual and normalized effort




q Calibrated coefficients for the linear
  effort estimation models
                  Model Evaluation
q 𝑅 ? for the two calibrated models




q 𝑀𝑀𝑅𝐸 and 𝑃𝑅𝐸𝐷(.25) for the linear models




q Hypothesis tests to evaluate the significance of the estimates
                           Conclusions
•   The preliminary calibration results have shown linear relationships exist
    between the proposed size metrics and project effort.
•   Linear regression shows the linear models fit the data set well in terms of
    MMRE, PRED(.25), and R? . MMRE and PRED(.25) are not accuracy indices
    since they are calculated based on the training dataset.
•   Extended Use Case Points model is superior to Early Use Case Points model for
    its higher value for R? and the lower value for MMRE.
•   Further evaluation of the estimation accuracy is needed, which requires more
    data points to be collected.
                   Future Directions
•   More data points need to be collected to draw conclusions about the
    estimation accuracy of the models, and also to evaluate if the superiority of
    EXUCP model over EUCP model is significant.
•   Supporting software tools need to be developed to streamline the process
    of training and testing the models.
•   Explore applicability of the evaluation metrics on more types of UML
    diagrams.
•   Extend the proposed metrics to other software management decisions, for
    example, resource allocation, schedule estimation, design quality
    assessment, etc.
                   Survey Link
•   http://52.15.204.194:8081/surveyproject
Thanks! & Questions?
                                    References-I
1.   B. W. Boehm, Software cost estimation with Cocomo II. Upper Saddle River, NJ: Prentice Hall, 2000.
2.   B. W. Boehm, J. A. Lane, S. Koolmanojwong, and . A. . Turner, Richard, The incremental commitment spiral
     model: principles and practices for successful systems and software. Upper Saddle River, NJ: Addison- Wesley,
     2014.
3.   I. Jacobson, Object-oriented software engineering: a use case driven approach. [New York] :Wokingham, Eng.
     ;Reading, Mass: ACM Press;Addison-Wesley Pub, 1992.
4.   D. Rosenberg, M. Stephens, and M. Collins-Cope, Agile development with ICONIX process: people, process, and
     pragmatism. Berkeley, CA: Apress, 2005.
5.   B. W. Boehm, Software engineering economics. Englewood Cliffs, N.J: Prentice-Hall, 1981.
6.   M. Stephens, D. Rosenberg, and I. Books24x7, Design driven testing: test smarter, not harder, 1st ed. New York:
     Apress, 2010;2011;.
7.   A. Cockburn, Writing Effective Use Cases, ser. Agile Software Development Series. Addison-Wesley, 2001.
     [Online]. Available: https://books.google.com/books?id=VKJQAAAAMAAJ
8.   M. Stephens, D. Rosenberg, and I. Books24x7, Design driven testing: test smarter, not harder, 1st ed.
     New York: Apress, 2010;2011;.
9.   A. Cockburn, Writing Effective Use Cases, ser. Agile Software Development Series. Addison-Wesley,
     2001. [Online]. Available: https://books.google.com/books?id=VKJQAAAAMAAJ
                                  References-II

10.   I. S. Group, “Getting a good start with better requirement management use case driven
      development,” IBM Rational Software, 2014.
11.   G. Karner, “Metrics for objectory. diploma thesis,” Ph.D. dissertation, University of Linkoping, 1993.
12.   A. J. Albrecht, “Measuring application development productivity,” in Proc. of the Joint
      SHARE/GUIDE/IBM Applicaiton Development Sym- posium, 1979, pp. 83–92.
13.   A. Albrecht, “Function point analysis,” in Encyclopedia of Software Engineering. Wiley, 1994, vol. 1,
      pp. 518–524.
14.   K. Periyasamy and A. Ghode, “Cost estimation using extended use case point (e-ucp) model,” 2009,
      pp. 1–5.
15.   M. M. Kirmani and A. Wahid, “Revised use case point (re-ucp) model for software effort estimation,”
      International Journal of Advanced Computer Science and Applications, vol. 6, no. 3, pp. 65–71, 2015.
16.   F. Wang, X. Yang, X. Zhu, and L. Chen, “Extended use case points method for software cost
      estimation,” 2009, pp. 1–5.
17.   W. G. Cochran, “Errors of measurement in statistics,” Technometrics, vol. 10, no. 4, pp. 637–666,
      1968.
