// use serde_json::{json, Value};
// use std::collections::HashMap;

// use chidian_core::JsonContainer;
// use chidian_core::dicts::get;
// use chidian_core::partials as p;


// mod fixtures {
//     use serde_json::{json, Value};
//     use std::collections::HashMap;

//     pub fn simple_data() -> Value {
//         json!({
//             "data": {
//                 "patient": {
//                     "id": "abc123",
//                     "active": true
//                 }
//             },
//             "list_data": [
//                 {
//                     "patient": {
//                         "id": "def456",
//                         "active": false
//                     }
//                 },
//                 {
//                     "patient": {
//                         "id": "ghi789",
//                         "active": true
//                     }
//                 },
//                 {
//                     "patient": {
//                         "id": "jkl101112",
//                         "active": true
//                     }
//                 }
//             ]
//         })
//     }

//     pub fn list_data() -> Value {
//         json!([
//             {
//                 "patient": {
//                     "id": "def456",
//                     "active": false
//                 }
//             },
//             {
//                 "patient": {
//                     "id": "ghi789",
//                     "active": true
//                 }
//             },
//             {
//                 "patient": {
//                     "id": "jkl101112",
//                     "active": true
//                 }
//             }
//         ])
//     }

//     pub fn nested_data() -> Value {
//         json!({
//             "data": [
//                 {
//                     "patient": {
//                         "id": "abc123",
//                         "active": true,
//                         "ints": [1, 2, 3],
//                         "dicts": [
//                             {
//                                 "num": 1,
//                                 "text": "one",
//                                 "inner": { "msg": "hello" }
//                             },
//                             {
//                                 "num": 2,
//                                 "text": "two",
//                                 "inner": { "msg": "world" }
//                             }
//                         ],
//                         "dict": {
//                             "char": "A",
//                             "inner": { "msg": "first letter" }
//                         }
//                     }
//                 },
//                 {
//                     "patient": {
//                         "id": "def456",
//                         "active": false,
//                         "ints": [4, 5, 6],
//                         "dicts": [
//                             {
//                                 "num": 3,
//                                 "text": "three",
//                                 "inner": { "msg": "hello" }
//                             },
//                             {
//                                 "num": 4,
//                                 "text": "four",
//                                 "inner": { "msg": "world" }
//                             }
//                         ],
//                         "dict": {
//                             "char": "B",
//                             "inner": { "msg": "second letter" }
//                         }
//                     }
//                 },
//                 {
//                     "patient": {
//                         "id": "ghi789",
//                         "active": true,
//                         "ints": [7, 8, 9],
//                         "dicts": [
//                             {
//                                 "num": 5,
//                                 "text": "five",
//                                 "inner": { "msg": "hello" }
//                             },
//                             {
//                                 "num": 6,
//                                 "text": "six",
//                                 "inner": { "msg": "world" }
//                             }
//                         ],
//                         "dict": {
//                             "char": "C",
//                             "inner": { "msg": "third letter" }
//                         }
//                     }
//                 },
//                 {
//                     "patient": {
//                         "id": "jkl101112",
//                         "active": true,
//                         "ints": null,
//                         "dicts": [
//                             {
//                                 "num": 7,
//                                 "text": "seven",
//                                 "inner": { "msg": "hello" }
//                             }
//                         ],
//                         "dict": {
//                             "char": "D",
//                             "inner": { "msg": "fourth letter" }
//                         }
//                     }
//                 }
//             ]
//         })
//     }
// }

// #[test]
// fn test_get() {
//     let source = fixtures::simple_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();

//     // Basic paths
//     assert_eq!(
//         get(source_container.clone(), "data", None).unwrap().data,
//         source["data"]
//     );
    
//     assert_eq!(
//         get(source_container.clone(), "data.patient.id", None).unwrap().data,
//         source["data"]["patient"]["id"]
//     );
    
//     assert_eq!(
//         get(source_container.clone(), "data.patient.active", None).unwrap().data,
//         source["data"]["patient"]["active"]
//     );
    
//     // With apply function
//     let modified_id = get(source_container.clone(), "data.patient.id", Some(p::append_string("_modified"))).unwrap().data;
//     assert_eq!(modified_id.as_str().unwrap(), "abc123_modified");
    
//     // Missing key should be an error
//     assert!(get(source_container.clone(), "data.nonexistent", None).is_err());
// }

// #[test]
// fn test_get_index() {
//     let source = fixtures::simple_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();

//     // Indexing (single_index)
//     assert_eq!(
//         get(source_container.clone(), "list_data[0].patient", None).unwrap().data,
//         source["list_data"][0]["patient"]
//     );
    
//     assert_eq!(
//         get(source_container.clone(), "list_data[1].patient", None).unwrap().data,
//         source["list_data"][1]["patient"]
//     );
    
//     // Out of bounds index should be an error
//     assert!(get(source_container.clone(), "list_data[5000].patient", None).is_err());
    
//     assert_eq!(
//         get(source_container.clone(), "list_data[-1].patient", None).unwrap().data,
//         source["list_data"][2]["patient"]  // Last element
//     );
    
//     // Slicing (multi_index)
//     let slice1_3 = get(source_container.clone(), "list_data[1:3]", None).unwrap().data;
//     let expected1_3 = json!([source["list_data"][1], source["list_data"][2]]);
//     assert_eq!(slice1_3, expected1_3);
    
//     let slice1_end = get(source_container.clone(), "list_data[1:]", None).unwrap().data;
//     let expected1_end = json!([source["list_data"][1], source["list_data"][2]]);
//     assert_eq!(slice1_end, expected1_end);
    
//     let slice0_2 = get(source_container.clone(), "list_data[:2]", None).unwrap().data;
//     let expected0_2 = json!([source["list_data"][0], source["list_data"][1]]);
//     assert_eq!(slice0_2, expected0_2);
    
//     let slice_all = get(source_container.clone(), "list_data[:]", None).unwrap().data;
//     assert_eq!(slice_all, source["list_data"]);
    
//     // Slice then index (multi_index -> single_index)
//     let slice1_3_patient = get(source_container.clone(), "list_data[1:3].patient", None).unwrap().data;
//     let expected1_3_patient = json!([source["list_data"][1]["patient"], source["list_data"][2]["patient"]]);
//     assert_eq!(slice1_3_patient, expected1_3_patient);
    
//     // Similar assertions for other slicing patterns...
// }

// #[test]
// fn test_get_from_list() {
//     let list_data = fixtures::list_data();
//     let source_container = JsonContainer::try_from(list_data.clone()).unwrap();
    
//     // Test all patients
//     let all_patients = get(source_container.clone(), "[*].patient", None).unwrap().data;
//     let expected_all_patients = json!([
//         list_data[0]["patient"],
//         list_data[1]["patient"],
//         list_data[2]["patient"]
//     ]);
//     assert_eq!(all_patients, expected_all_patients);
    
//     // Test all patient IDs
//     let all_patient_ids = get(source_container.clone(), "[:].patient.id", None).unwrap().data;
//     let expected_all_patient_ids = json!([
//         list_data[0]["patient"]["id"],
//         list_data[1]["patient"]["id"],
//         list_data[2]["patient"]["id"]
//     ]);
//     assert_eq!(all_patient_ids, expected_all_patient_ids);
    
//     // Test sliced patient IDs
//     let sliced_patient_ids = get(source_container.clone(), "[0:2].patient.id", None).unwrap().data;
//     let expected_sliced_patient_ids = json!([
//         list_data[0]["patient"]["id"],
//         list_data[1]["patient"]["id"]
//     ]);
//     assert_eq!(sliced_patient_ids, expected_sliced_patient_ids);
    
//     // Test negative slice patient IDs
//     let negative_slice_patient_ids = get(source_container.clone(), "[-2:].patient.id", None).unwrap().data;
//     let expected_negative_slice_patient_ids = json!([
//         list_data[1]["patient"]["id"],
//         list_data[2]["patient"]["id"]
//     ]);
//     assert_eq!(negative_slice_patient_ids, expected_negative_slice_patient_ids);
// }

// #[test]
// fn test_nested_get() {
//     let source = fixtures::nested_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();
    
//     // Test basic array mapping
//     let patient_active = get(source_container.clone(), "data[*].patient.active", None).unwrap().data;
//     assert_eq!(patient_active, json!([true, false, true, true]));
    
//     let patient_ids = get(source_container.clone(), "data[*].patient.id", None).unwrap().data;
//     assert_eq!(patient_ids, json!(["abc123", "def456", "ghi789", "jkl101112"]));
    
//     // Test with arrays and null values
//     let patient_ints = get(source_container.clone(), "data[*].patient.ints", None).unwrap().data;
//     assert_eq!(patient_ints, json!([[1, 2, 3], [4, 5, 6], [7, 8, 9], null]));
    
//     // Test with flatten option
//     let flatten_options = p::options_with_flatten(true);
//     let patient_ints_flat = get(source_container.clone(), "data[*].patient.ints", Some(flatten_options)).unwrap().data;
//     assert_eq!(patient_ints_flat, json!([1, 2, 3, 4, 5, 6, 7, 8, 9]));
    
//     // Test nested array mapping
//     let patient_dict_nums = get(source_container.clone(), "data[*].patient.dicts[*].num", None).unwrap().data;
//     assert_eq!(patient_dict_nums, json!([[1, 2], [3, 4], [5, 6], [7]]));
    
//     // Test nested array mapping with flatten
//     let patient_dict_nums_flat = get(source_container.clone(), "data[*].patient.dicts[*].num", Some(flatten_options)).unwrap().data;
//     assert_eq!(patient_dict_nums_flat, json!([1, 2, 3, 4, 5, 6, 7]));
    
//     // Test missing keys
//     assert!(get(source_container.clone(), "missing.key", None).is_err());
//     assert!(get(source_container.clone(), "missing[*].key", None).is_err());
//     assert!(get(source_container.clone(), "missing[*].key[*].here", None).is_err());
//     assert!(get(source_container.clone(), "data[8888].patient", None).is_err());
// }


// #[test]
// fn test_get_apply() {
//     let source = fixtures::simple_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();
    
//     let old_str = "456";
//     let new_str = "FourFiveSix";
    
//     // Single apply function (uppercase)
//     let single_apply = p::to_uppercase();
//     let id_upper = get(source_container.clone(), "data.patient.id", Some(single_apply)).unwrap().data;
//     assert_eq!(id_upper.as_str().unwrap(), "ABC123");
    
//     // Chained apply functions
//     let chained_apply = p::chain(vec![
//         p::to_uppercase(),
//         p::replace_string(old_str, new_str)
//     ]);
    
//     // Test on list item id
//     let list_id_transformed = get(source_container.clone(), "list_data[0].patient.id", Some(chained_apply.clone())).unwrap().data;
//     let expected = "DEF456".replace(old_str, new_str);
//     assert_eq!(list_id_transformed.as_str().unwrap(), expected);
    
//     // Failed chain should return Err
//     let failed_chain_apply = p::chain(vec![
//         p::to_uppercase(),
//         p::always_none(), // This breaks the chain
//         p::replace_string(old_str, new_str)
//     ]);
    
//     assert!(get(source_container.clone(), "list_data[0].patient.id", Some(failed_chain_apply)).is_err());
    
//     // Apply on missing key should return Err
//     assert!(get(source_container.clone(), "data.notFoundKey", Some(p::to_uppercase())).is_err());
// }

// #[test]
// fn test_get_only_if() {
//     let source = fixtures::simple_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();
    
//     let key = "data.patient.id";
    
//     // Passes check (starts with "abc")
//     let starts_with_abc = p::with_filter(
//         p::starts_with("abc"),
//         p::to_uppercase()
//     );
    
//     let passes_check = get(source_container.clone(), key, Some(starts_with_abc)).unwrap().data;
//     assert_eq!(passes_check.as_str().unwrap(), "ABC123");
    
//     // Fails check (starts with "000") - should error
//     let starts_with_000 = p::with_filter(
//         p::starts_with("000"),
//         p::to_uppercase()
//     );
    
//     assert!(get(source_container.clone(), key, Some(starts_with_000)).is_err());
// }

// #[test]
// fn test_get_single_key_tuple() {
//     let source = fixtures::simple_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();
    
//     // Handle tuple case
//     let tuple_result = get(source_container.clone(), "data.patient.(id,active)", None).unwrap().data;
//     let expected_tuple = json!([
//         source["data"]["patient"]["id"],
//         source["data"]["patient"]["active"]
//     ]);
//     assert_eq!(tuple_result, expected_tuple);
    
//     // Allow whitespace within brackets
//     let tuple_with_space = get(source_container.clone(), "data.patient.( id, active )", None).unwrap().data;
//     assert_eq!(tuple_with_space, tuple_result);
    
//     // Include missing key in tuple
//     let tuple_with_missing = get(source_container.clone(), "data.patient.(id,active,missingKey)", None).unwrap().data;
//     let expected_with_missing = json!([
//         source["data"]["patient"]["id"],
//         source["data"]["patient"]["active"],
//         null
//     ]);
//     assert_eq!(tuple_with_missing, expected_with_missing);
    
//     // Expect list unwrapping to still work
//     let list_tuple = get(source_container.clone(), "list_data[*].patient.(id, active)", None).unwrap().data;
//     let expected_list_tuple = json!([
//         [source["list_data"][0]["patient"]["id"], source["list_data"][0]["patient"]["active"]],
//         [source["list_data"][1]["patient"]["id"], source["list_data"][1]["patient"]["active"]],
//         [source["list_data"][2]["patient"]["id"], source["list_data"][2]["patient"]["active"]]
//     ]);
//     assert_eq!(list_tuple, expected_list_tuple);
    
//     // Test default value for tuple items
//     let default_value = "Missing!";
//     let tuple_with_default = get(
//         source_container.clone(), 
//         "data.patient.(id, active, missingKey)", 
//         Some(p::with_default(default_value))
//     ).unwrap().data;
    
//     let expected_with_default = json!([
//         source["data"]["patient"]["id"],
//         source["data"]["patient"]["active"],
//         default_value
//     ]);
//     assert_eq!(tuple_with_default, expected_with_default);
    
//     // Test apply onto tuple (get index 1)
//     let get_index_1 = get(
//         source_container.clone(),
//         "data.patient.(id, active, missingKey)",
//         Some(p::index(1))
//     ).unwrap().data;
//     assert_eq!(get_index_1, source["data"]["patient"]["active"]);
    
//     // Test apply to keep only first 2 elements
//     let keep_first_two = get(
//         source_container.clone(),
//         "data.patient.(id, active, missingKey)",
//         Some(p::keep(2))
//     ).unwrap().data;
    
//     let expected_first_two = json!([
//         source["data"]["patient"]["id"],
//         source["data"]["patient"]["active"]
//     ]);
//     assert_eq!(keep_first_two, expected_first_two);
    
//     // Test only_if filtering
//     let filter_always_false = p::with_filter(p::always_false(), p::identity());
//     assert!(get(
//         source_container.clone(),
//         "data.patient.(id, active, missingKey)",
//         Some(filter_always_false)
//     ).is_err());
// }

// #[test]
// fn test_get_nested_key_tuple() {
//     let source = fixtures::nested_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();
    
//     // Single item example
//     let single_item = get(
//         source_container.clone(),
//         "data[0].patient.dicts[0].(num, text)",
//         None
//     ).unwrap().data;
    
//     let expected_single_item = json!([
//         source["data"][0]["patient"]["dicts"][0]["num"],
//         source["data"][0]["patient"]["dicts"][0]["text"]
//     ]);
//     assert_eq!(single_item, expected_single_item);
    
//     // More complex nested path in tuple
//     let nested_path_tuple = get(
//         source_container.clone(),
//         "data[0].patient.dicts[0].(num, inner.msg)",
//         None
//     ).unwrap().data;
    
//     let expected_nested_path = json!([
//         source["data"][0]["patient"]["dicts"][0]["num"],
//         source["data"][0]["patient"]["dicts"][0]["inner"]["msg"]
//     ]);
//     assert_eq!(nested_path_tuple, expected_nested_path);
    
//     // Multi-item example
//     let multi_item = get(
//         source_container.clone(),
//         "data[*].patient.dict.(char, inner.msg)",
//         None
//     ).unwrap().data;
    
//     let expected_multi_item = json!([
//         [source["data"][0]["patient"]["dict"]["char"], source["data"][0]["patient"]["dict"]["inner"]["msg"]],
//         [source["data"][1]["patient"]["dict"]["char"], source["data"][1]["patient"]["dict"]["inner"]["msg"]],
//         [source["data"][2]["patient"]["dict"]["char"], source["data"][2]["patient"]["dict"]["inner"]["msg"]],
//         [source["data"][3]["patient"]["dict"]["char"], source["data"][3]["patient"]["dict"]["inner"]["msg"]]
//     ]);
//     assert_eq!(multi_item, expected_multi_item);
    
//     // Multi-item on multi-[*] example
//     let multi_multi = get(
//         source_container.clone(),
//         "data[*].patient.dicts[*].(num, inner.msg)",
//         None
//     ).unwrap().data;
    
//     let expected_multi_multi = json!([
//         [
//             [source["data"][0]["patient"]["dicts"][0]["num"], source["data"][0]["patient"]["dicts"][0]["inner"]["msg"]],
//             [source["data"][0]["patient"]["dicts"][1]["num"], source["data"][0]["patient"]["dicts"][1]["inner"]["msg"]]
//         ],
//         [
//             [source["data"][1]["patient"]["dicts"][0]["num"], source["data"][1]["patient"]["dicts"][0]["inner"]["msg"]],
//             [source["data"][1]["patient"]["dicts"][1]["num"], source["data"][1]["patient"]["dicts"][1]["inner"]["msg"]]
//         ],
//         [
//             [source["data"][2]["patient"]["dicts"][0]["num"], source["data"][2]["patient"]["dicts"][0]["inner"]["msg"]],
//             [source["data"][2]["patient"]["dicts"][1]["num"], source["data"][2]["patient"]["dicts"][1]["inner"]["msg"]]
//         ],
//         [
//             [source["data"][3]["patient"]["dicts"][0]["num"], source["data"][3]["patient"]["dicts"][0]["inner"]["msg"]]
//         ]
//     ]);
//     assert_eq!(multi_multi, expected_multi_multi);
// }

// #[test]
// fn test_get_strict() {
//     let source = fixtures::nested_data();
//     let source_container = JsonContainer::try_from(source.clone()).unwrap();
    
//     // Simple key example
//     let missing_key = "some.key.nope.notthere";
    
//     // Normal mode - already returns Err for missing keys in this implementation
//     assert!(get(source_container.clone(), missing_key, None).is_err());
    
//     // Strict mode - should return a more specific error
//     let strict_option = p::options_with_strict(true);
//     let strict_result = get(source_container.clone(), missing_key, Some(strict_option));
//     assert!(strict_result.is_err());
    
//     // Ideally we could check the error type/message is different between strict and non-strict
//     // But we'll need the actual implementation to test that properly
// }